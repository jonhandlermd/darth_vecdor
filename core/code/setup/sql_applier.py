

#  Copyright (c) 2025 Keylog Solutions LLC
#
#  ATTRIBUTION NOTICE: This work was conceived and created by Jonathan A. Handler. Large language model(s) and/or many other resources were used to help create this work.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import shutil
import sys
import json
import re
from pathlib import Path
from jinja2 import Template
from sqlalchemy import Index, MetaData, text, inspect, TextClause, UniqueConstraint, ForeignKeyConstraint, Table
from sqlalchemy.dialects import postgresql
from dataclasses import dataclass
from typing import Optional
import app_source.public_repo.core.code.utilities.debug as debug
from app_source.public_repo.core.code.interactors.db_orm import enhanced_db_class, dec_base as Base
import app_source.public_repo.core.configs.file_locations as fl
import app_source.public_repo.core.configs.orm_db_configs as odc

gl_d = debug.default_d

# Regex to identify expected prefix in filenames (e.g., 000000001_dv_filename.sql)
PREFIX_PATTERN = re.compile(r"^(\d{9})_dv_(.+\.sql)$")

@dataclass
class table_info_class:
    """
    Encapsulates mapping between an ORM-declared table and its reflected DB counterpart.
    """
    key: str                 # SQLAlchemy metadata key, e.g., 'public.users'
    short_name: str          # Unqualified table name, e.g., 'users'
    schema: str              # Schema name, e.g., 'public'
    full_name: str           # Qualified name for SQL, e.g., 'public.users'
    model_table: Table       # ORM Table object from Base.metadata
    db_table: Optional[Table]  # Reflected Table object or None if missing


class sql_applier_class:
    def __init__(self, enhanced_db_obj: enhanced_db_class, dry_run=False):
        """
        Initialize the SQL applier with necessary database object.
        Prepares directory paths and ensures required folders exist.
        """
        self.enhanced_db_obj = enhanced_db_obj
        self.dry_run = dry_run

        self.base_dir = Path(fl.setup_sqls_path)
        self.state_dir = Path(fl.sql_state_path)
        self.deprecated = Path(fl.sql_deprecated_path)
        self.failed = Path(fl.sql_failed_path)
        self.processed = self.base_dir / "processed"
        self.manifest = self.state_dir / "manifest.json"
        self.consider = self.base_dir / "for_consideration"

        # Ensure all necessary directories exist before processing
        for path in [self.processed, self.failed, *self.mode_folders.values(), self.state_dir, self.deprecated]:
            path.mkdir(parents=True, exist_ok=True)

        # Define status text for reports, easy to adjust wording centrally
        self.status_text = {
            "success": "Executed",
            "failed": "FAILED",
            "validation_error": "VALIDATION ERROR",
            "skipped": "SKIPPED",
            "archived": "Archived",
        }

        # Define emojis for TXT report only — these will NOT be saved to JSON or shown in HTML
        self.status_emojis = {
            "success": "✅",
            "failed": "❌",
            "validation_error": "⚠️",
            "skipped": "⏭️",
            "archived": "📦",
        }

        # Reflect the current state of the actual database schema (from Postgres)
        # Must do this in two separate lines.
        self.db_metadata = MetaData()
        self.db_metadata.reflect(bind=self.enhanced_db_obj.engine, schema=odc.schema)

        # Now hold teh state of the database as known by ORM
        self.orm_metadata = Base.metadata

        # Populate info about tables, since different thigns refer to tables
        # in different ways (e.g., with/without the schema)
        # Build a list of TableInfo objects for auto-complete and centralized access
        self.table_infos: list[table_info_class] = []
        for model_table in self.orm_metadata.tables.values():
            self.table_infos.append(table_info_class(
                    key=model_table.key,
                    short_name=model_table.name,
                    schema=model_table.schema or odc.schema,
                    full_name=f"{model_table.schema or odc.schema}.{model_table.name}",
                    db_table = self.db_metadata.tables.get(model_table.key),
                    model_table=model_table
                    )
                )

    @staticmethod
    def index_exists_on_columns(table, columns):
        """
        Check if any index exists on the table with exactly the same columns (in order).
        """
        cols_names = [col.name for col in columns]
        for idx in table.indexes:
            idx_cols = [col.name for col in idx.columns]
            if idx_cols == cols_names:
                return True
        return False

    @staticmethod
    def generate_index_sql(index_name, table_name, column_names, schema=None):
        """
        Generate a CREATE INDEX SQL string, with optional schema support.
        """
        quoted_cols = ", ".join(f'"{col}"' for col in column_names)
        if schema:
            if schema == odc.schema:
                qualified_table = f'<replaceme_schema>.{table_name}'
            elif schema == odc.system_schema:
                qualified_table = f'<replaceme_system_schema>.{table_name}'
            else:
                raise Exception('Unrecgnized schema for index generation.')
        else:
            qualified_table = f'{table_name}'
        return {index_name: f'CREATE INDEX IF NOT EXISTS "{index_name}" ON {qualified_table} ({quoted_cols});'}

    def suggest_indexes_for_foreign_keys(self):
        suggested_sqls = []

        for table in self.db_metadata.tables.values():
            for column in table.columns:
                if column.foreign_keys:
                    if not self.index_exists_on_columns(table, [column]):
                        index_name = f"ix_{table.name}_{column.name}_fk"
                        schema = table.schema or None  # fall back to default
                        sql = self.generate_index_sql(index_name, table.name, [column.name], schema=schema)
                        suggested_sqls.append(sql)

        return suggested_sqls

    @staticmethod
    def is_valid_filename(name):
        # Allow alphanumerics, underscores, and dashes. Reject others.
        return re.fullmatch(r"[a-zA-Z0-9_\-]+", name) is not None

    def write_sql_suggestions_to_file(self, sql_statements):
        """
        Write each SQL statement to its own file,.
        Overwrite if the file exists. Raise exception for invalid filenames.

        :param sql_statements: List[Dict[str, str]]
        """
        self.consider.mkdir(parents=True, exist_ok=True)
        output_dir = self.consider

        count = 0
        for stmt_dict in sql_statements:
            if not isinstance(stmt_dict, dict) or len(stmt_dict) != 1:
                raise ValueError(f"Each item must be a dict with one key-value pair. Got: {stmt_dict}")

            file_name, sql = next(iter(stmt_dict.items()))

            if not self.is_valid_filename(file_name):
                raise ValueError(f"Invalid index name for filename: '{file_name}'")

            file_path = output_dir / f"{file_name}.sql"

            with open(file_path, "w") as f:
                f.write(sql.strip() + "\n")
                count += 1

        debug.debug(f"Wrote {count} SQL suggestion(s) to individual .sql files in: {output_dir}", d=gl_d)

    def analyze_and_suggest_fk_indexes(self):
        """
        Main entry point: Reflect DB schema and suggest missing FK indexes.
        """
        suggestions = self.suggest_indexes_for_foreign_keys()
        self.write_sql_suggestions_to_file(suggestions)

    @property
    def mode_folders(self):
        """Define all supported mode directories."""
        return {
            "pending_prepend_number": self.base_dir / "pending_prepend_number",
            "pending_keep_number": self.base_dir / "pending_keep_number",
            "pending_update_number": self.base_dir / "pending_update_number",
            "manually_run_prepend_number": self.base_dir / "manually_run_prepend_number",
            "manually_run_keep_number": self.base_dir / "manually_run_keep_number",
            "manually_run_renumber": self.base_dir / "manually_run_renumber",
        }

    @property
    def all_mode_dirs(self):
        return list(self.mode_folders.values())

    @staticmethod
    def log_and_exit(msg):
        """Log the message and exit the program."""
        debug.log(__file__, msg)
        sys.exit(msg)

    @staticmethod
    def extract_number(name):
        """Extract batch number from a filename prefix if present."""
        match = PREFIX_PATTERN.match(name)
        return int(match.group(1)) if match else 0

    def generate_next_number(self):
        """
        Determine the next batch number based on already processed and failed files.
        Looks at existing files with proper prefix and picks max + 1.
        """
        all_files = list(self.processed.glob("*.sql")) + list(self.failed.glob("*.sql"))
        numbers = [self.extract_number(f.name) for f in all_files if PREFIX_PATTERN.match(f.name)]
        return max(numbers, default=0) + 1

    def load_manifest(self):
        """Load the existing manifest.json if present, else return empty list."""
        if self.manifest.exists():
            with open(self.manifest, "r") as f:
                content = f.read().strip()
                return json.loads(content) if content else []
        return []

    def save_manifest(self, entries):
        """
        Write entries back to the manifest file.
        Also generates human-readable sidecar reports: .txt and .html for easy viewing.
        """
        if not entries:
            # Nothing to save if manifest is empty
            return

        with open(self.manifest, "w") as f:
            json.dump(entries, f, indent=2)
        self.generate_reports(entries)

    def generate_reports(self, manifest_entries):
        """
        Generate human-readable sidecar reports:
        - A plain text summary listing all runs with filenames and statuses (with emojis)
        - An HTML report for easy viewing in browsers with clear run/batch grouping (no emojis)
        """
        txt_path = self.state_dir / "manifest_report.txt"
        html_path = self.state_dir / "manifest_report.html"

        # Write plain text report, grouping by run
        with open(txt_path, "w") as f:
            current_run = None
            for entry in manifest_entries:
                if entry["run_number"] != current_run:
                    current_run = entry["run_number"]
                    f.write(f"\n=== Run {current_run} | Batch {entry['batch']} ===\n")
                emoji = self.status_emojis.get(entry['status'], "")
                status_display = self.status_text.get(entry['status'], entry['status'])
                # Show emoji + status_text in TXT only
                status_line = f"  - {emoji} {status_display}: {entry['filename']}"
                if 'error' in entry:
                    status_line += f" — {entry['error']}"
                f.write(status_line + "\n")

        # HTML report with runs grouped and separated visually (NO emojis)
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>SQL Applier Manifest Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h2 { border-bottom: 2px solid #444; padding-bottom: 4px; margin-top: 40px; }
                table { border-collapse: collapse; width: 100%; margin-top: 10px; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                tr:nth-child(even) { background-color: #f9f9f9; }
                tr:hover { background-color: #eaeaea; }
                .status-success { color: green; font-weight: bold; }
                .status-failed { color: red; font-weight: bold; }
                .status-validation_error { color: orange; font-weight: bold; }
                .status-skipped { color: gray; font-style: italic; }
                .status-archived { color: blue; font-weight: bold; }
            </style>
        </head>
        <body>
            <h1>SQL Applier Manifest Report</h1>
            {% for run_number, run_entries in manifest_entries|groupby('run_number') %}
                <h2>Run {{ run_number }} | Batch {{ run_entries[0]['batch'] if run_entries else 'N/A' }}</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Status</th>
                            <th>Filename</th>
                            <th>Origin</th>
                            <th>Error</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for entry in run_entries %}
                        <tr>
                            <td class="status-{{ entry.status|replace(' ', '_') }}">{{ status_text.get(entry.status, entry.status) }}</td>
                            <td>{{ entry.filename }}</td>
                            <td>{{ entry.origin }}</td>
                            <td>{{ entry.error if 'error' in entry else '' }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            {% endfor %}
        </body>
        </html>
        """

        # Render HTML with Jinja2 Template, passing status_text dict for display
        html = Template(html_template).render(manifest_entries=manifest_entries, status_text=self.status_text)
        with open(html_path, "w") as f:
            f.write(html)

    def validate_filenames(self):
        """
        Validate filenames across all mode directories before processing.
        Rules:
        - Filenames must be lowercase.
        - Filenames can only contain lowercase a-z, 0-9, '_', '-', '.' characters.
        - Base filename length must be <= 100 characters.
        - Extract base name after prefix (if any) for validation.
        If invalid, logs error and exits immediately.
        """
        VALID_FILENAME = re.compile(r"^[a-z0-9._-]+\.sql$")
        MAX_FILENAME_LENGTH = 100
        valid_files = []
        for mode_dir in self.all_mode_dirs:
            for file in mode_dir.glob("*.sql"):
                # Check uppercase letters not allowed
                if any(c.isalpha() and not c.islower() for c in file.name):
                    self.log_and_exit(f"❌ File {file.name} contains uppercase characters. All filenames must be lowercase.")
                basename = file.name
                match = PREFIX_PATTERN.match(basename)
                if match:
                    basename = match.group(2)
                if not VALID_FILENAME.match(basename):
                    self.log_and_exit(f"❌ File {file.name} contains invalid characters. Only lowercase a-z, 0-9, '_', '-', '.' are allowed.")
                if len(basename) > MAX_FILENAME_LENGTH:
                    self.log_and_exit(f"❌ File {file.name} is too long (> {MAX_FILENAME_LENGTH} chars).")
                valid_files.append(file)
        return valid_files

    @staticmethod
    def check_for_attr_and_not_null(obj, attr):
        if not hasattr(obj, attr):
            return False
        if getattr(obj, attr) is None:
            return False
        return True

    @staticmethod
    def extract_server_default(col):
        """
        Normalize the server default of a SQLAlchemy Column object into a plain string.
        Handles both TextClause and raw string defaults gracefully.
        """
        if not col.server_default:
            return None
        arg = col.server_default.arg
        if isinstance(arg, TextClause):
            return str(arg.text).strip()
        return str(arg).strip()


    def suggest_column_drift_sql(self):
        """
        Generate ALTER TABLE statements for column-level drift:
          - missing columns
          - nullability mismatches
          - server default mismatches

        Uses self.table_info_obj.table_infos (List[TableInfo]).
        """
        drift_sqls = []

        for info in self.table_infos:
            if not self.check_for_attr_and_not_null(info, 'db_table'):
                # Table missing entirely in DB
                continue

            for col_name, model_col in info.model_table.columns.items():
                db_col = info.db_table.columns.get(col_name, None)

                model_def = self.extract_server_default(model_col)
                db_def = self.extract_server_default(db_col) if db_col is not None else None

                # 1) Missing column
                if db_col is None:
                    # col_type = str(model_col.type)
                    # Need to do this instead of above line, otherwise do not get timestamp with timezone, etc.
                    col_type = model_col.type.compile(dialect=postgresql.dialect())
                    nullable_sql = ' NOT NULL' if not model_col.nullable else ''
                    default_sql = f" DEFAULT {model_def}" if model_def is not None else ''
                    sql = (
                        f"ALTER TABLE {info.full_name} "
                        f"ADD COLUMN {col_name} {col_type}{nullable_sql}{default_sql};"
                    )
                    drift_sqls.append({f"addcol_{info.short_name}_{col_name}": sql})
                    continue

                # 2) Nullability drift
                if model_col.nullable != db_col.nullable:
                    action = 'DROP NOT NULL' if model_col.nullable else 'SET NOT NULL'
                    sql = (
                        f"ALTER TABLE {info.full_name} "
                        f"ALTER COLUMN {col_name} {action};"
                    )
                    drift_sqls.append({f"null_{info.short_name}_{col_name}": sql})

                # 3) Default drift
                if model_def != db_def:
                    if model_def is None and db_def is not None:
                        # drop existing default
                        sql = (
                            f"ALTER TABLE {info.full_name} "
                            f"ALTER COLUMN {col_name} DROP DEFAULT;"
                        )
                        drift_sqls.append({f"defdrop_{info.short_name}_{col_name}": sql})
                    else:
                        # add or change default
                        sql = (
                            f"ALTER TABLE {info.full_name} "
                            f"ALTER COLUMN {col_name} SET DEFAULT {model_def};"
                        )
                        key = 'defadd' if db_def is None else 'defchg'
                        drift_sqls.append({f"{key}_{info.short_name}_{col_name}": sql})

        return drift_sqls

    def suggest_fk_constraint_drift_sql(self):
        """
        Generate ALTER TABLE statements for missing or mismatched foreign keys.
        """
        drift_sqls = []

        for info in self.table_infos:
            if self.check_for_attr_and_not_null(info, 'db_table'):
                continue

            # Build a set of existing DB FK signatures
            if self.check_for_attr_and_not_null(info, 'db_table') and self.check_for_attr_and_not_null(info.db_table, 'constraints'):
                db_fks = set(
                    (
                        tuple(el.parent.name for el in fk.elements),
                        f"{fk.elements[0].column.table.schema or info.schema}.{fk.elements[0].column.table.name}",
                        tuple(el.column.name for el in fk.elements)
                    )
                    for fk in info.db_table.constraints
                    if isinstance(fk, ForeignKeyConstraint)
                )
            else:
                db_fks = set(())

            for constraint in info.model_table.constraints:
                if not isinstance(constraint, ForeignKeyConstraint):
                    continue

                # Local column names participating in FK
                local_cols = tuple(el.parent.name for el in constraint.elements)

                # Referenced table & columns
                ref_table = constraint.elements[0].column.table
                remote_table = f"{ref_table.schema or info.schema}.{ref_table.name}"
                remote_cols = tuple(el.column.name for el in constraint.elements)

                sig = (local_cols, remote_table, remote_cols)
                if sig in db_fks:
                    continue  # FK exists correctly

                # Suggest creating missing FK
                fk_name = constraint.name or f"fk_{info.short_name}_{'_'.join(local_cols)}"
                col_list = ", ".join(local_cols)
                ref_cols = ", ".join(remote_cols)
                sql = (
                    f"ALTER TABLE {info.full_name} "
                    f"ADD CONSTRAINT {fk_name} FOREIGN KEY ({col_list}) "
                    f"REFERENCES {remote_table} ({ref_cols});"
                )
                drift_sqls.append({f"addfk_{info.short_name}_{fk_name}": sql})

        return drift_sqls

    def suggest_unique_constraint_drift_sql(self):
        """
        Generate ALTER TABLE statements for missing UNIQUE constraints.
        """
        drift_sqls = []

        for info in self.table_infos:
            if not self.check_for_attr_and_not_null(info, 'db_table'):
                continue

            # Existing DB uniques
            if self.check_for_attr_and_not_null(info.db_table, 'constraints'):
                db_uniques = {tuple(sorted(c.columns.keys()))
                              for c in info.db_table.constraints
                              if isinstance(c, UniqueConstraint)}
            else:
                db_uniques = {}

            # ORM-defined uniques
            for constraint in info.model_table.constraints:
                if not isinstance(constraint, UniqueConstraint):
                    continue
                cols = tuple(sorted(col.name for col in constraint.columns))
                if cols not in db_uniques:
                    uq_name = constraint.name or f"uq_{info.short_name}_{'_'.join(cols)}"
                    col_list = ", ".join(cols)
                    sql = (
                        f"ALTER TABLE {info.full_name} "
                        f"ADD CONSTRAINT {uq_name} UNIQUE ({col_list});"
                    )
                    drift_sqls.append({f"adduq_{info.short_name}_{'_'.join(cols)}": sql})

        return drift_sqls

    def suggest_all_drift_sql(self):
        """
        Unified entry point for all drift suggestions.
        """
        return (
                self.suggest_column_drift_sql()
                + self.suggest_fk_constraint_drift_sql()
                + self.suggest_unique_constraint_drift_sql()
        )


    def run(self):
        """
        Main execution method to run SQL batch processing.

        Workflow:
        0. Analyze DB ORM and suggest indexes not already present but likely useful.
        1. Validate filenames across all modes.
        2. Ensure exactly one mode folder contains files to process.
        3. Determine the batch number for this run.
        4. Based on mode, validate and rename files as needed.
        5. Execute SQL files or archive manual files.
        6. Move processed files into the processed folder with proper batch prefix.
        7. Move failed files to the failed folder and log errors.
        8. Update the manifest with batch and file metadata.
        """

        debug.debug("🟡 Starting sql applier...", d=gl_d)

        # Suggest indexes
        self.analyze_and_suggest_fk_indexes()

        # Suggest SQL "drift" corrections
        drift_suggestions = self.suggest_all_drift_sql()
        self.write_sql_suggestions_to_file(drift_suggestions)

        # Validate the file names
        valid_files = self.validate_filenames()

        # Determine which mode folder is active
        active_mode = None
        for mode, folder in self.mode_folders.items():
            if any(folder.glob("*.sql")):
                if active_mode:
                    self.log_and_exit("❌ Error: Multiple pending/manually_run modes have files. Only one allowed at a time.")
                active_mode = mode

        if not active_mode:
            debug.debug("ℹ️  No SQL files found in any mode folder. Nothing to do.", d=gl_d)
            return

        folder = self.mode_folders[active_mode]
        files = sorted(folder.glob("*.sql"), key=lambda f: f.name)

        # Load existing manifest entries and determine run number
        manifest_entries = self.load_manifest()
        run_number = max((entry.get("run_number", 0) for entry in manifest_entries), default=0) + 1

        batch_number = self.generate_next_number()
        first_error = None
        batch_log = []
        logged_files = set()  # To prevent duplicate manifest entries for same file

        # Validate prepend_number mode files to ensure no prefix exists
        if "prepend_number" in active_mode:
            for f in files:
                if PREFIX_PATTERN.match(f.name):
                    error_msg = f"File {f.name} already has a prefix but is in prepend mode"
                    batch_log.append({"run_number": run_number, "batch": batch_number, "filename": f.name,
                                      "origin": "manual" if "manually" in active_mode else "auto",
                                      "status": "validation_error", "error": error_msg})
                    logged_files.add(f.name)
                    first_error = first_error or error_msg

        for file in files:
            original_name = file.name
            error_message = None

            # Determine target filename based on mode
            if "keep_number" in active_mode:
                match = PREFIX_PATTERN.match(original_name)
                if not match:
                    error_message = f"File {original_name} missing valid 9-digit_dv_ prefix"
                else:
                    file_number = int(match.group(1))
                    if file_number > batch_number + len(files):
                        error_message = f"File {original_name} has prefix too far in the future"
                new_name = original_name if not error_message else None

            elif "update_number" in active_mode:
                match = PREFIX_PATTERN.match(original_name)
                if not match:
                    error_message = f"File {original_name} missing valid 9-digit_dv_ prefix"
                    new_name = None
                else:
                    new_name = f"{batch_number:09d}_dv_{match.group(2)}"
            else:
                new_name = f"{batch_number:09d}_dv_{original_name}"

            # Handle validation errors, but log only once per file
            if error_message:
                if original_name not in logged_files:
                    batch_log.append({"run_number": run_number, "batch": batch_number, "filename": original_name,
                                      "origin": "manual" if "manually" in active_mode else "auto",
                                      "status": "validation_error", "error": error_message})
                    logged_files.add(original_name)
                first_error = first_error or error_message
                continue

            full_dest = self.processed / new_name
            # Prevent overwriting existing processed file
            if full_dest.exists():
                error_message = f"{new_name} already exists in processed/"
                if original_name not in logged_files:
                    batch_log.append({"run_number": run_number, "batch": batch_number, "filename": original_name,
                                      "origin": "manual" if "manually" in active_mode else "auto",
                                      "status": "validation_error", "error": error_message})
                    logged_files.add(original_name)
                first_error = first_error or error_message
                continue

            origin = "manual" if "manually_run" in active_mode else "auto"

            # If any validation error exists, mark this file as skipped (once only)
            if first_error:
                if original_name not in logged_files:
                    batch_log.append({"run_number": run_number, "batch": batch_number, "filename": new_name,
                                      "origin": origin, "status": "skipped", "error": "Skipped due to validation error in at least one other file in this batch."})
                    logged_files.add(original_name)
                continue

            if origin == "manual":
                # Archive manual-run files by moving them
                shutil.move(str(file), str(full_dest))
                debug.debug(f"Archived manual: {new_name}", d=gl_d)
                batch_log.append({"run_number": run_number, "batch": batch_number, "filename": new_name,
                                  "origin": origin, "status": "archived"})
                continue

            # Automatic SQL execution path
            try:
                with open(file, "r") as f:
                    query = f.read()
                    # Replace placeholders with configured schema names
                    query = query.replace('<replaceme_schema>', odc.schema)
                    query = query.replace('<replaceme_system_schema>', odc.system_schema)

                if not self.dry_run:
                    success = self.enhanced_db_obj.do_no_result_query(query, ())
                    if not success:
                        msg = f"Query execution returned False for query: {query}"
                        debug.log(__file__, msg)
                        raise Exception("Query execution returned False")

                shutil.move(str(file), str(full_dest))
                debug.debug(f"Executed: {new_name}", d=gl_d)
                batch_log.append({"run_number": run_number, "batch": batch_number, "filename": new_name,
                                  "origin": origin, "status": "success"})

            except Exception as e:
                failed_path = self.failed / new_name
                shutil.move(str(file), str(failed_path))
                msg = f"FAILED: {file.name} - {e}"
                batch_log.append({"run_number": run_number, "batch": batch_number, "filename": new_name,
                                  "origin": origin, "status": "failed", "error": str(e)})
                debug.log(__file__, msg)
                break  # Stop execution on first SQL failure

        # Only extend manifest if there is anything to add (prevents empty manifest writes)
        if batch_log:
            manifest_entries.extend(batch_log)
            self.save_manifest(manifest_entries)
            debug.debug("Done with sql applier.", d=gl_d)

        # Exit with first validation error if any
        if first_error:
            self.log_and_exit(first_error)

