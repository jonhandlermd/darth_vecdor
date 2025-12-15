


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

from sentence_transformers import SentenceTransformer, SimilarityFunction
# from sentence_transformers.losses import DenoisingAutoEncoderLoss
# from langchain_community.embeddings import SentenceTransformerEmbeddings # Need to pip install, see here for info: https://pypi.org/project/langchain-community/
# import copy
#### If i don't do this I get an error that the name Dataset is not defined.
#### The SentenceTransformer fit_mixin.py module dynamically imports Dataset if datasets is available,
#### but part of the code doesn't seem to
#### handle it appropriately if Dataset is not imported, so... will import it here.
import os
import app_source.public_repo.core.configs.other_configs as oc
import torch
import torch.nn.functional as F

d = oc.d


# Embedding Object Class for Sentence Transformer
class embedding_class:

    def __init__(self, sentence, sent_tran_obj):

        # Initialize properties
        self.full_embedding = None
        self.cls_embedding = None
        self.mean_pooling = None
        self.max_pooling = None
        self.tokenizer_output = None
        self.confidence = None

        # Set property values
        self._get_embedding(sentence, sent_tran_obj)

    # Do mean pooling of embeddings
    @staticmethod
    def _do_mean_pooling(embeddings, attention_mask):
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(embeddings.size()).float()
        sum_embeddings = torch.sum(embeddings * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        return sum_embeddings / sum_mask

    # Do max pooling of embeddings
    @staticmethod
    def _do_max_pooling(embeddings, attention_mask):
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(embeddings.size()).float()
        embeddings[input_mask_expanded == 0] = -1e9  # Set padding tokens to large negative value
        return torch.max(embeddings, 1)[0]

    # Function to get the full token embedding
    def _get_embedding(self, sentence, sent_tran_obj):

        """
        Based on my research, the SentenceTransfomer encode will produce the exact same result as the manual mean pooling result that I have coded here. It will automatically tokenize the sentence and then enocde it in embedding with mean pooling of the resulting tokens. Based on examination of the underlying code, I think the mean pooling is hard-coded. There are other forms of pooling, but mean is hard-coded with the encode function. 
        
        I also see no difference in encoding if I lower-case everything or not. I'm not sure if that's becasue the encode function will do that for me or if the PubMed BERT model I was using is simply case insensitive.

        The encode auto-tokenizes the string, and it seems to give the same result when I tokenize it using the tokenizing function and then manually do the embedding and pooling. But... if I manually create my own tokenizer, it's probably not good because the regular tokenizer from the model does things like split up words into smaller chunks if it doesn't know them, and does other things too like truncating if the sentence is longer than can the SentenceTransformer can handle. So, best not to do my own tokenization, I think. However, that may be worth confirming or looking into going forward.
        """

        self.tokenizer_output = sent_tran_obj.model.tokenize([sentence])

        input_ids = self.tokenizer_output['input_ids'].squeeze()
        tokens = sent_tran_obj.model.tokenizer.convert_ids_to_tokens(input_ids)
        self.similarity_confidence = 100
        for token in tokens:
            if '#' in token:
                # print(sentence, token)
                self.similarity_confidence -= 100/(len(tokens) - 2)

        for key in self.tokenizer_output:
            self.tokenizer_output[key] = self.tokenizer_output[key].to(sent_tran_obj._device)
        transformer_model = sent_tran_obj.model[0].auto_model
        with torch.no_grad():
            outputs = transformer_model(**self.tokenizer_output)
        self.full_embedding = outputs.last_hidden_state.to(sent_tran_obj._device)  # full embedding

        self.cls_embedding = outputs.last_hidden_state[:, 0, :].to(sent_tran_obj._device) # cls embedding
        self.mean_pooling = self._do_mean_pooling(self.full_embedding, self.tokenizer_output['attention_mask'])
        self.max_pooling = self._do_max_pooling(self.full_embedding, self.tokenizer_output['attention_mask'])
        self.concat_pooling = torch.cat([self.cls_embedding, self.mean_pooling, self.max_pooling], dim=-1)

        self.cls_embedding = F.normalize(self.cls_embedding, p=2, dim=1)
        self.mean_pooling = F.normalize(self.mean_pooling, p=2, dim=1)
        self.max_pooling = F.normalize(self.max_pooling, p=2, dim=1)
        # Normalizing the embeddings after concatenation, ensures that the entire
        # concatenated representation has unit length, making it suitable for tasks such as similarity comparison.
        # Therefore, we don't concatenate the normalized components, we concatenate then normalize.
        # However, this may be worth reconsidering. There are some potential benefits to normalizing then normalizing again.
        # In practice on single anecdote, not sure it helped.
        self.concat_pooling = F.normalize(self.concat_pooling, p=2, dim=1)
        self.geom_average = abs(self.cls_embedding * self.mean_pooling * self.max_pooling)**(1.0000/3.0000)
        self.arith_average = (self.cls_embedding + self.mean_pooling + self.max_pooling)/3

        return

# Class for Sentence Transformer
class sent_tran_class:

    def __init__(self, src_loc, dest_loc=None):

        # Initialize vars
        self.src_loc = src_loc
        self.dest_loc = dest_loc

        # If we didn't get a src_loc then raise an error
        if not self.src_loc:
            raise Exception

        #### Initialize model
        self.model = None

        # Need to do this if want to get CLS
        self._device = torch.device("mps" if torch.backends.mps.is_built() else "cpu")

        #### Download model if requested to do so
        if self.src_loc and self.dest_loc:
            self._download(self.src_loc, self.dest_loc)
        #### Load if requested to do so
        else:
            self._load()

        if src_loc:
            self.model_name = self.src_loc

    def _load(self):

        #### Load requested pretrained model
        if d: print(f"Loading {self.src_loc} pre-trained transformer.")
        os.environ["TOKENIZERS_PARALLELISM"] = "true"
        self.model = SentenceTransformer.load(self.src_loc).to(self._device)
        # self.model.to('cpu') # PROVEN: THIS IS WAYYY SLOWER!!!
        if d: print(f"Model device: {self.model.device}")
        if d: print(f"Done loading {self.src_loc} pre-trained transformer.")


    def _download(self, src_loc, dest_loc):
        #### Simply calling it causes the model to be downloaded
        if d: print(f"Downloading {src_loc} pre-trained transformer.")
        self.model = SentenceTransformer(src_loc)
        if d: print(f"Downloaded {src_loc} pre-trained transformer.")

        #### Now, just need to save it in desired location
        if d: print(f"Saving {src_loc} pre-trained transformer to {dest_loc}.")
        self.model.save_pretrained(dest_loc)
        if d: print(f"Saved {src_loc} pre-trained transformer to {dest_loc}.")


    def phrase_alts_to_vector(self, phrases):
        # Hold list of embeddings for each phrase in list
        embedded_cls_list = []
        # Get embeddings for each phrase in phrases list
        for phrase in phrases:
            embedded_phrase_obj = embedding_class(phrase, self)
            embedded_cls_list.append(embedded_phrase_obj.cls_embedding)

        # Now get average of the CLS tokens
        # Stack the list into a single tensor of shape (num_sentences, embedding_dim)
        stacked_cls_tokens = torch.stack(embedded_cls_list)

        # Calculate the mean along axis 0 (across the sentences)
        mean_cls_token = torch.mean(stacked_cls_tokens, dim=0)
        return mean_cls_token


    def get_similarity(self, tpair, do_cls=False):

        #### Calculate embeddings
        emb_obj_1 = embedding_class(tpair[0], self)
        emb_obj_2 = embedding_class(tpair[1], self)
        # embeddings = self.model.encode(tpair)

        #### Each embedding is a vector
        #vector_s1 = embeddings[0]
        #vector_s2 = embeddings[1]
        # vector_s1 = emb_obj_1.full_embedding
        # vector_s2 = emb_obj_2.full_embedding
        vector_s1 = emb_obj_1.cls_embedding
        vector_s2 = emb_obj_2.cls_embedding
        #### Next line returns same result as: np.dot(vector_s1, vector_s2) / (np.linalg.norm(vector_s1) * np.linalg.norm(vector_s2))

        #### Determine similarity
        self.model.similarity_fn_name = SimilarityFunction.COSINE # With new code, don't think this does anything.
        t_sim = F.cosine_similarity(vector_s1, vector_s2, dim=1)
        #t_sim = self.model.similarity(embeddings, embeddings)
        #t_sim = 1/(1 + np.exp(-t_sim)) # Sigmoid function
        return t_sim



