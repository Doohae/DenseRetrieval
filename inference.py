import numpy as np
import time
from tqdm import tqdm
from pprint import pprint

import torch
from datasets import load_dataset


def raw_inference(retriever, valid_dataset):
    idx = np.random.randint(len(valid_dataset))
    query = valid_dataset[idx]["question"]

    print(f"[Search Query] \n{query}\n")
    print(f"[Ground Truth Passage]")
    pprint(valid_dataset[idx]['context'])

    start = time.time()
    results = retriever.get_relevant_doc(query=query, k=3)
    end = time.time()

    indices = results.tolist()
    print(f"Took {end-start}s Retrieving For Single Question")
    for i, idx in enumerate(indices):
        print(f"Top-{i + 1}th Passage (Index {idx})")
        pprint(retriever.valid_corpus[idx])


def faiss_inference(
    p_encoder,
    q_encoder,
    tokenizer,
    valid_dataset,
    device
):
    ds_with_embeddings = valid_dataset.map(lambda example: {"embeddings": p_encoder(**tokenizer(example["context"],
                                                                                                padding="max_length",
                                                                                                truncation=True,
                                                                                                return_tensors="pt").to(device).squeeze().cpu().numpy())})
    ds_with_embeddings.add_faiss_index(column='embeddings', device=0)

    # Validation Set의 전체 질문들에 대한 embedding 구해놓
    question_embedding = []
    for question in tqdm(valid_dataset["question"]):
        tokenized = tokenizer(question, padding="max_length", truncation=True, return_tensors="pt").to(device)
        encoded = q_encoder(**tokenized).squeeze().detach().cpu().numpy()
        question_embedding.append(encoded)

    question_embedding = np.array(question_embedding)

    start = time.time()
    # 여러 개 한번에 retrieval
    scores, retrieved_examples = ds_with_embeddings.get_nearest_examples_batch('embeddings', question_embedding, k=3)
    end = time.time()
    print(f"Took {end-start}s Retreiving the Whole Validation Dataset")
    pprint(retrieved_examples[0]["context"])
    print(retrieved_examples[0]["question"])

    # 개별 query retrieval
    retrieved = ds_with_embeddings.get_nearest_examples('embeddings', question_embedding[0], k=3)
    pprint(retrieved[1]["context"])

    idx = np.random.randint(len(valid_dataset))
    print(f"[Question]\n{valid_dataset['question'][idx]}")
    print(f"[Ground Truth]\n{valid_dataset['context'][idx]}")
    retrieved_docs = retrieved_examples[idx]["context"]
    for i, doc in enumerate(retrieved_docs):
        print(f"Top-{i + 1}th Passage")
        pprint(doc)

if __name__ == "__main__":
    valid_dataset = load_dataset("klue", "mrc", split="validation")

    torch.set_grad_enabled(False)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
