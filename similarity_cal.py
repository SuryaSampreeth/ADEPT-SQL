
from user_input_process import user_input_init
from call_emb import callm3e, vectorize_localmodel
from typing import Type
from sklearn.metrics.pairwise import cosine_similarity

import pandas as pd
import numpy as np
import os

current_dir = os.getcwd()


def similarity(vec1, vec2):
    return cosine_similarity(
        np.array(vec1).reshape(1, -1),
        np.array(vec2).reshape(1, -1)
    )[0][0]


def search_qvec(full_processed_user_input: Type[user_input_init], emb, threshold=0.85):
    """
    CSR Module: Contextual SQL Retriever.
    Vectorizes the masked user question and compares it against stored QS pair vectors.
    
    Returns:
        (not_found_flag: bool, info: str, found_df: DataFrame)
        not_found_flag=True means zero-shot branch; False means few-shot branch.
    """
    # Embed the masked (processed) question
    if emb.get('name') != 'local model':
        new_vec = callm3e(emb).init_prompt(full_processed_user_input.trans).call()
    else:
        new_vec = vectorize_localmodel(full_processed_user_input.trans)

    if new_vec == 'Emb Fail':
        print('[CSR] Embedding failed. Defaulting to zero-shot.')
        return True, 'Embedding failed', pd.DataFrame()

    qvec_path = os.path.join(current_dir, 'backend/qvec.csv')
    if not os.path.exists(qvec_path):
        print('[CSR] qvec.csv not found. Defaulting to zero-shot.')
        return True, 'No QS store found', pd.DataFrame()

    qvec_df = pd.read_csv(qvec_path)
    found_df = pd.DataFrame(columns=['question', 'sql', 'similarity'])

    for i in range(qvec_df.shape[0]):
        try:
            stored_vec = eval(qvec_df['qvec'][i])
            if not isinstance(stored_vec, list):
                continue
            sim = similarity(new_vec, stored_vec)
            print(f'[CSR] Q#{i} similarity: {sim:.4f} | "{qvec_df["question"][i][:60]}"')

            if sim > threshold:
                found_df = pd.concat([found_df, pd.DataFrame([{
                    'question': qvec_df.iloc[i]['question'],
                    'sql': qvec_df.iloc[i]['sql'],
                    'similarity': sim
                }])], ignore_index=True)
        except Exception as e:
            print(f'[CSR] Skipping row {i} due to error: {e}')
            continue

    if found_df.shape[0] < 1:
        return True, 'No similar Questions found (zero-shot)', found_df
    else:
        found_df = found_df.sort_values('similarity', ascending=False).reset_index(drop=True)
        return False, f'{found_df.shape[0]} similar Question-SQL pair(s) found (few-shot)', found_df


if __name__ == "__main__":
    emb = {"name": "local model", "url": "", "token": ""}
    inp = user_input_init("Did Blake book Adan Dinning?").full_process()
    not_found, info, found_df = search_qvec(inp, emb)
    print(not_found, info)
    print(found_df)
