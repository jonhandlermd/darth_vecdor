# Prologue
I had a "conversation" with ChatGPT about my code. I had asked it a question, and it thought that I was not "doing it right" and therefore had incurred some risks. When I described those design decisions as intentional, the "light bulb" or "aha" moment seemed to occur for ChatGPT, and it declared that I was using a thoughtful pattern akin to the "Active Record" from Ruby on Rails. I had never heard of Active Record, but was happy to know someone else had done something similar. I asked ChatGPT to write up an explanation of its understanding of my design philosophy and approach here. The following is what it wrote. I hope it's adequately accurate and helpful.

# Background and Design Intent

The design described in this document was not arrived at accidentally, nor was it the result of misunderstanding SQLAlchemy. It was already fully implemented before this documentation was written.

At the beginning of discussion and review, I (ChatGPT) initially interpreted the code through the lens of **standard SQLAlchemy usage**, which typically assumes a Unit-of-Work model with long-lived sessions, deferred persistence, identity maps, and explicit commit management at the application layer.

Under that assumption, several patterns appeared unconventional.

However, as the discussion progressed, it became clear that this interpretation was incorrect—not because the code was flawed, but because it was operating under a **different, intentionally chosen persistence philosophy**.

Through explanation of design goals and concrete behavior, it became evident that:

- Object instantiation was intentionally coupled to persistence
- Constructor-based upsert behavior was deliberate, not accidental
- SQLAlchemy sessions were being used narrowly and explicitly
- ORM objects were treated as stable representations of persisted state
- The design strongly resembled an **Active Record-style mental model**, rather than SQLAlchemy’s default Unit-of-Work approach

Crucially, this model was not adopted reactively or as a workaround. It had already been implemented because it aligned better with the author’s goals: reducing cognitive overhead, preventing forgotten persistence, minimizing session lifetime risks, and making object creation an explicit act with immediate, durable effect.

Once this intent was understood, it became clear that the codebase is not “misusing” SQLAlchemy, but rather **using it in a consciously different mode**—one that prioritizes clarity, safety, and correctness over implicit state management and deferred writes.

This document exists to make that intent explicit, so that future readers do not incorrectly assume standard SQLAlchemy semantics and misinterpret deliberate design decisions as mistakes.

---

# SQLAlchemy Usage Philosophy and Design Rationale

## Overview

This codebase uses SQLAlchemy in a **deliberate, opinionated way** that differs from the classic “Unit of Work” style commonly presented in SQLAlchemy documentation.

SQLAlchemy is used primarily as:

- A **schema-aware object model**
- A **type-safe, IDE-discoverable interface to the database**
- A **self-persisting object factory** for writes
- A **short-lived, explicitly scoped query interface** for reads

The design emphasizes **clarity of intent**, **transaction safety**, and **ease of correct usage**, even when that means deviating from default ORM patterns.

This is an intentional architectural choice.

---

## Important Terminology Note: “Sessions”

Throughout this document, the term **“session”** refers to a **SQLAlchemy database session**, *not* a Flask (web) session.

- **Flask sessions** may be long-lived and represent user or request context.
- **SQLAlchemy sessions** represent database transaction scope and are intentionally kept short-lived.

These are distinct concepts and should not be conflated.

---

## Core Philosophy

### Objects Represent Real Database Rows

In this system:

> **If a Python ORM object is manually instantiated, the corresponding database row is expected to exist immediately.**

Manual object creation implies intent to persist.

Objects are not treated as:
- “pending”
- “dirty”
- “awaiting flush”

This avoids situations where objects exist in memory but are never written to the database.

Objects loaded via ORM queries follow standard SQLAlchemy behavior and bypass constructor logic entirely.

---

### Persistence Is Explicit and Intentional

Persistence occurs only where it is explicitly intended.

Some ORM classes perform **upsert logic at instantiation time** when created manually.  
This behavior is deliberate and limited in scope.

After instantiation:
- No additional database writes occur automatically
- Attribute mutation does **not** imply persistence
- Downstream changes must be explicitly persisted if desired

This mirrors standard SQLAlchemy semantics (nothing is written without a commit) while automating the initial persistence step for safety and clarity.

---

### Constructor-Based Upsert

When an ORM object is manually instantiated:

- An upsert ensures the corresponding row exists
- A primary key is immediately available
- The object becomes a valid reference without requiring a separate save call

When an ORM object is loaded via a SQLAlchemy query:

- The constructor is bypassed
- No persistence logic is triggered
- The object behaves exactly as a standard SQLAlchemy ORM instance

This cleanly separates:
- **Object creation** from
- **Object materialization**

---

## SQLAlchemy Session Usage

### Short-Lived SQLAlchemy Sessions (Predominant Pattern)

SQLAlchemy sessions are intentionally:

- Created narrowly
- Used briefly
- Explicitly scoped
- Immediately closed

This ensures:

- No lingering connections
- No unintended locks
- No forgotten commits
- No hidden transaction boundaries

Sessions are typically used for:
- A single write operation
- A discrete read query
- A bounded batch operation

---

### Long-Running SQLAlchemy Sessions (Intentional, Limited Use)

In some cases—such as processing large datasets or iterating over large query results—a SQLAlchemy session may remain open for longer durations.

In these scenarios:

- The session is still explicitly scoped
- Its lifetime is intentional and bounded
- It is primarily used for **reads**
- It is not relied upon for implicit persistence or state tracking

The distinction is not “short vs long,” but **whether the session is responsible for managing mutable persistence state**.

---

## Object Mutability by Convention

ORM objects in this system are generally treated as **immutable representations of persisted state**.

Once instantiated and upserted:

- Their values are not expected to change
- They are not treated as live, session-managed entities
- They are not relied upon for dirty-state tracking

If values must change, those changes are expected to be:
- Explicit
- Intentional
- Clearly persisted

This avoids ambiguity around whether modifications are saved.

---

## How This Differs from Classic SQLAlchemy Usage

### Classic SQLAlchemy Model

SQLAlchemy traditionally emphasizes:

- Long-lived sessions
- Unit-of-Work batching
- Deferred persistence
- Identity-map–managed object lifecycles
- Automatic dirty tracking

This model is powerful but requires careful discipline and can be error-prone when misused.

---

### This Codebase’s Model

This codebase prioritizes:

- Explicit persistence intent
- Atomic operations
- Minimal session state
- Reduced cognitive overhead
- Prevention of accidental non-persistence

The approach resembles an **ActiveRecord-style mental model**, even though SQLAlchemy is used as the underlying ORM.

This is a design choice, not a limitation.

---

## Trade-Offs (Accepted by Design)

This approach intentionally minimizes reliance on:

- ORM identity maps
- Lazy-loaded relationships
- Automatic change tracking across sessions
- Multi-object transactional batching

These features are powerful but unnecessary for this system’s usage patterns.

The simplicity, safety, and clarity gains outweigh those benefits here.

---

## Design Defaults, Not Absolutes

Statements such as *“always”* or *“never”* in this documentation describe **design defaults**, not immutable rules.

There may be:
- Performance-driven exceptions
- Explicit deviations
- Carefully managed special cases

What matters is that such cases are **intentional, visible, and understood**.

---

## Summary

This codebase uses SQLAlchemy as:

- A schema-aware modeling tool
- A safe persistence interface
- A guard against accidental non-writes
- A clarity-first abstraction over SQL

This is a deliberate and thoughtful deviation from classic SQLAlchemy usage, optimized for:

- Correctness
- Maintainability
- Explicit intent
- Low operational risk
