def split_paragraph(text:str):
    paragraph=[p.strip() for p in text.split("\n") if len(p.strip)>20]
    return paragraph

def chunk_documents(doc,chunk_size=500,overlap=100):
    paragraph=split_paragraph(doc["text"])
    metadata=doc["metadata"]

    chunks=[]
    current_chunk=""
    start=0

    for para in paragraph:
        if len(para) > chunk_size:
            sub_start = 0
            while sub_start < len(para):
                sub_chunk = para[sub_start:sub_start + chunk_size]

                chunks.append({
                    "text": sub_chunk,
                    "metadata": {
                        **metadata,
                        "chunk_type": "long_paragraph_split",
                        "chunk_start": sub_start,
                        "chunk_end": sub_start + chunk_size
                    }
                })
                sub_start=chunk_size-overlap
            continue
        if len(current_chunk)+len(para)<=chunk_size:
            current_chunk+=" "+para
        else:
            chunks.append({
                "text": current_chunk.strip(),
                "metadata": {
                    **metadata,
                    "chunk_type": "paragraph_group"
                }
            }) 

            current_chunk = para        
    if current_chunk:
           chunks.append({
            "text": current_chunk.strip(),
            "metadata": {
                **metadata,
                "chunk_type": "paragraph_group"
            }
        })

    return chunks      