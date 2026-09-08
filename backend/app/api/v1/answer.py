from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import get_db
from app.observability.tracing import trace_stage
from app.providers.embedding.factory import get_embedding_provider
from app.providers.reranking.factory import get_reranker_provider
from app.services.retrieval_service import RetrievalService
from app.services.rrf_service import RRFService
from app.services.reranker_service import RerankerService
from app.services.answer_service import AnswerService
from app.schemas.answer import AnswerRequest, AnswerResponse

router = APIRouter(prefix="/api/v1/answer", tags=["Answer"])


@router.post("", response_model=AnswerResponse)
def answer(request: AnswerRequest, db: Session = Depends(get_db)):
    retrieval_service = RetrievalService(get_embedding_provider())
    with trace_stage("vector_search", {"query": request.query}):
        vector_results = retrieval_service.vector_search(
            db=db, query=request.query, region=request.region, top_k=settings.RRF_TOP_K
        )
    with trace_stage("keyword_search", {"query": request.query}):
        keyword_results = retrieval_service.keyword_search(
            db=db, query=request.query, region=request.region, top_k=settings.RRF_TOP_K
        )

    with trace_stage("rrf", {"query": request.query}):
        rrf_results = RRFService.fuse(
            vector_results=vector_results,
            keyword_results=keyword_results,
            top_k=settings.RRF_TOP_K,
            k=settings.RRF_K,
        )

    with trace_stage("reranking", {"query": request.query}):
        reranked = RerankerService.rerank(
            query=request.query,
            results=rrf_results,
            reranker=get_reranker_provider(),
            top_k=request.top_k,
        )

    answer_service = AnswerService()
    result = answer_service.generate_answer(request.query, reranked)
    return AnswerResponse(answer=result["answer"], citations=result["citations"])
