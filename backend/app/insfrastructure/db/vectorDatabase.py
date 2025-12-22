import google.generativeai as genai
from supabase import create_client, Client
import os

class VectorService:
    def __init__(self):
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"), 
            os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        )
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

    async def get_embedding(self, text: str):
        # Gera o vetor usando o modelo mais atual do Google
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']

    async def search_similar_colleges(self, query_text: str, threshold=0.8):
        query_embedding = await self.get_embedding(query_text)
        
        # Chama a função RPC (que você criará no Supabase) para buscar similaridade
        rpc_params = {
            "query_embedding": query_embedding,
            "match_threshold": threshold,
            "match_count": 5
        }
        response = self.supabase.rpc("match_colleges", rpc_params).execute()
        return response.data