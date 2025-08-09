"""
문서 관리 API 엔드포인트
파일 업로드, 목록 조회, 삭제 기능을 제공합니다.
"""

import os
import shutil
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging
from datetime import datetime
import threading
import asyncio

from src.services.document_service import document_service
from src.services.rag_service import rag_service
from src.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# 업로드 디렉토리 설정
UPLOAD_DIR = "static/RAG"
# .doc는 명시적으로 차단하고 .docx만 허용
ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.docx', '.md', '.json', '.csv', '.xlsx', '.xls'}

class DocumentInfo(BaseModel):
    filename: str
    size: int
    upload_time: str
    file_type: str

class ProcessingStatus(BaseModel):
    queue_size: int
    processing_thread_alive: bool
    message: str

# 처리 중인 문서 상태 저장
processing_documents: Dict[str, Dict[str, Any]] = {}

def ensure_upload_dir():
    """업로드 디렉토리가 존재하는지 확인하고 없으면 생성합니다."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_file_extension(filename: str) -> str:
    """파일 확장자를 반환합니다."""
    return os.path.splitext(filename)[1].lower()

def is_allowed_file(filename: str) -> bool:
    """허용된 파일 형식인지 확인합니다."""
    return get_file_extension(filename) in ALLOWED_EXTENSIONS

def document_processing_callback(success: bool, doc_id: Optional[str], error: Optional[str]):
    """문서 처리 완료 콜백"""
    if success:
        logger.info(f"문서 처리 완료: {doc_id}")
        # 처리 완료된 문서 상태 업데이트
        for filename, status in list(processing_documents.items()):
            if status.get("doc_id") == "processing":
                processing_documents[filename]["status"] = "completed"
                processing_documents[filename]["doc_id"] = doc_id
                processing_documents[filename]["completed_at"] = datetime.now().isoformat()
                processing_documents[filename]["final_status"] = "completed"  # 최종 상태 표시
                
                # RAG 문서 자동 재로드
                try:
                    logger.info(f"문서 '{filename}' 처리 완료 후 RAG 자동 재로드 시작")
                    rag_result = rag_service.reload_rag_documents()
                    logger.info(f"RAG 자동 재로드 완료: {rag_result}")
                except Exception as e:
                    logger.error(f"RAG 자동 재로드 실패: {e}")
                
                # 60초 후 처리 완료된 문서 제거 (더 긴 시간으로 연장)
                import threading
                def remove_completed_document():
                    import time
                    time.sleep(60)
                    if filename in processing_documents:
                        del processing_documents[filename]
                        logger.info(f"처리 완료된 문서 '{filename}'을 목록에서 제거했습니다.")
                
                threading.Thread(target=remove_completed_document, daemon=True).start()
                break
    else:
        logger.error(f"문서 처리 실패: {error}")
        # 처리 실패된 문서 상태 업데이트
        for filename, status in list(processing_documents.items()):
            if status.get("doc_id") == "processing":
                processing_documents[filename]["status"] = "failed"
                processing_documents[filename]["error"] = error
                processing_documents[filename]["failed_at"] = datetime.now().isoformat()
                processing_documents[filename]["final_status"] = "failed"  # 최종 상태 표시
                # 60초 후 처리 실패한 문서 제거 (더 긴 시간으로 연장)
                import threading
                def remove_failed_document():
                    import time
                    time.sleep(60)
                    if filename in processing_documents:
                        del processing_documents[filename]
                        logger.info(f"처리 실패한 문서 '{filename}'을 목록에서 제거했습니다.")
                
                threading.Thread(target=remove_failed_document, daemon=True).start()
                break

@router.get("/api/documents", response_model=List[DocumentInfo])
async def get_documents():
    """
    업로드된 문서 목록을 반환합니다.
    """
    try:
        ensure_upload_dir()
        documents = []
        
        for filename in os.listdir(UPLOAD_DIR):
            file_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                documents.append(DocumentInfo(
                    filename=filename,
                    size=stat.st_size,
                    upload_time=datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    file_type=get_file_extension(filename)
                ))
        
        # 파일명 순으로 정렬
        documents.sort(key=lambda x: x.filename)
        return documents
        
    except Exception as e:
        logger.error(f"문서 목록 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail="문서 목록을 불러오는 중 오류가 발생했습니다.")

@router.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    문서를 업로드하고 벡터 저장소에 처리합니다.
    """
    try:
        ensure_upload_dir()
        
        # 파일 형식 검증
        if not is_allowed_file(file.filename):
            raise HTTPException(
                status_code=400, 
                detail=f"지원하지 않는 파일 형식입니다. 허용된 형식: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # 파일 크기 검증 (50MB 제한)
        if file.size and file.size > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="파일 크기는 50MB를 초과할 수 없습니다.")
        
        # 파일명 중복 처리
        filename = file.filename
        file_path = os.path.join(UPLOAD_DIR, filename)
        counter = 1
        
        while os.path.exists(file_path):
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{counter}{ext}"
            file_path = os.path.join(UPLOAD_DIR, filename)
            counter += 1
        
        # 파일 저장
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"문서 업로드 완료: {filename} (크기: {file.size} bytes)")
        
        # 문서 처리 시작 (비동기)
        try:
            # PDF 파일인 경우 특별 처리
            file_extension = get_file_extension(filename).lower()
            if file_extension == '.pdf':
                logger.info(f"PDF 문서 전처리 시작: {filename}")
            # .doc은 업로드 차단 (이 단계까지 오지 않도록 ALLOWED_EXTENSIONS에서 제외되어 있지만, 이중 방어)
            if file_extension == '.doc':
                raise HTTPException(status_code=400, detail=".doc 형식은 지원하지 않습니다. .docx로 변환 후 업로드해주세요.")
            
            # .docx인 경우 Word 전용 파이프라인으로 위임 처리
            if file_extension == '.docx':
                from src.api.endpoints.word_embedding import get_word_embedding_service
                service = get_word_embedding_service()
                # Word 전용 서비스는 임시 파일 기반 처리이므로 그대로 경로 전달
                result = service.process_word_document(file_path, {
                    "source": "upload",
                    "upload_time": datetime.now().isoformat(),
                    "file_size": file.size,
                    "file_type": file_extension
                })
                logger.info(f"워드 전용 파이프라인 처리 완료: {filename} -> chunks: {result.get('total_chunks', 0)}")
                # 고유 식별자 생성 (파일명 기반)
                doc_id = f"word::{filename}"
                # 처리 상태 기록 후 즉시 응답 (비동기 큐 미사용 경로)
                processing_documents[filename] = {
                    "status": "completed",
                    "doc_id": doc_id,
                    "completed_at": datetime.now().isoformat(),
                    "filename": filename,
                    "file_size": file.size,
                    "file_type": file_extension,
                    "text_length": result.get("total_tokens", 0),
                    "final_status": "completed"
                }
                return JSONResponse(
                    status_code=200,
                    content={
                        "message": "워드(.docx) 문서가 전용 파이프라인으로 처리되었습니다.",
                        "filename": filename,
                        "doc_id": doc_id,
                        "status": "completed",
                        "file_size": file.size,
                        "file_type": file_extension,
                        "total_chunks": result.get("total_chunks", 0),
                        "total_tokens": result.get("total_tokens", 0),
                        "text_length": result.get("total_tokens", 0)
                    }
                )

            content = document_service.load_document(file_path)
            
            if not content.strip():
                raise ValueError("문서에서 텍스트를 추출할 수 없습니다.")
            
            logger.info(f"문서 텍스트 추출 완료: {filename} (길이: {len(content)} 문자)")
            
            # 처리 상태 초기화
            processing_documents[filename] = {
                "status": "processing",
                "doc_id": "processing",
                "started_at": datetime.now().isoformat(),
                "filename": filename,
                "file_size": file.size,
                "file_type": file_extension,
                "text_length": len(content)
            }
            
            # 비동기 처리 시작 (파일명을 캡처하는 콜백 래퍼 사용)
            def _completion_callback(success: bool, doc_id: Optional[str], error: Optional[str], target_filename: str = filename):
                try:
                    if target_filename not in processing_documents:
                        logger.warning(f"처리 완료 콜백: 상태 테이블에 파일을 찾을 수 없음: {target_filename}")
                        return
                    if success:
                        processing_documents[target_filename]["status"] = "completed"
                        processing_documents[target_filename]["doc_id"] = doc_id
                        processing_documents[target_filename]["completed_at"] = datetime.now().isoformat()
                        processing_documents[target_filename]["final_status"] = "completed"
                        # RAG 문서 자동 재로드
                        try:
                            logger.info(f"문서 '{target_filename}' 처리 완료 후 RAG 자동 재로드 시작")
                            rag_result = rag_service.reload_rag_documents()
                            logger.info(f"RAG 자동 재로드 완료: {rag_result}")
                        except Exception as e:
                            logger.error(f"RAG 자동 재로드 실패: {e}")
                        # 60초 후 목록에서 제거
                        def _remove_later(fname: str = target_filename):
                            import time
                            time.sleep(60)
                            if fname in processing_documents:
                                del processing_documents[fname]
                                logger.info(f"처리 완료된 문서 '{fname}'을 목록에서 제거했습니다.")
                        threading.Thread(target=_remove_later, daemon=True).start()
                    else:
                        processing_documents[target_filename]["status"] = "failed"
                        processing_documents[target_filename]["error"] = error
                        processing_documents[target_filename]["failed_at"] = datetime.now().isoformat()
                        processing_documents[target_filename]["final_status"] = "failed"
                        # 60초 후 목록에서 제거
                        def _remove_failed_later(fname: str = target_filename):
                            import time
                            time.sleep(60)
                            if fname in processing_documents:
                                del processing_documents[fname]
                                logger.info(f"처리 실패한 문서 '{fname}'을 목록에서 제거했습니다.")
                        threading.Thread(target=_remove_failed_later, daemon=True).start()
                except Exception as e:
                    logger.error(f"처리 완료 콜백 처리 중 오류: {e}")

            doc_id = document_service.process_document(
                content=content,
                filename=filename,
                metadata={
                    "source": "upload",
                    "file_size": file.size,
                    "file_type": file_extension,
                    "text_length": len(content),
                    "upload_time": datetime.now().isoformat()
                },
                callback=_completion_callback
            )
            
            return JSONResponse(
                status_code=200,
                content={
                    "message": "문서가 업로드되었고 처리 중입니다.",
                    "filename": filename,
                    "doc_id": doc_id,
                    "status": "processing",
                    "file_size": file.size,
                    "text_length": len(content),
                    "file_type": file_extension
                }
            )
            
        except Exception as e:
            logger.error(f"문서 처리 시작 실패: {filename}, 오류: {e}")
            # 파일 삭제
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"실패한 파일 삭제: {file_path}")
            
            error_message = f"문서 처리 중 오류가 발생했습니다: {str(e)}"
            if "PDF" in str(e):
                error_message += " (PDF 파일이 손상되었거나 텍스트를 추출할 수 없습니다.)"
            
            raise HTTPException(status_code=500, detail=error_message)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문서 업로드 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail="문서 업로드 중 오류가 발생했습니다.")

@router.get("/api/documents/processing-status")
async def get_processing_status() -> ProcessingStatus:
    """
    문서 처리 상태를 반환합니다.
    """
    try:
        queue_status = document_service.get_queue_status()
        
        return ProcessingStatus(
            queue_size=queue_status["queue_size"],
            processing_thread_alive=queue_status["processing_thread_alive"],
            message=f"큐 크기: {queue_status['queue_size']}, 처리 스레드: {'활성' if queue_status['processing_thread_alive'] else '비활성'}"
        )
    except Exception as e:
        logger.error(f"처리 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="처리 상태 조회 중 오류가 발생했습니다.")

@router.get("/api/documents/processing-documents")
async def get_processing_documents() -> Dict[str, Any]:
    """
    처리 중인 문서 목록을 반환합니다.
    """
    try:
        # 실제로 진행 중인 문서만 반환 (완료/실패 항목 제외)
        active_docs = {fn: st for fn, st in processing_documents.items() if st.get("status") == "processing"}
        return {
            "processing_documents": active_docs,
            "count": len(active_docs)
        }
    except Exception as e:
        logger.error(f"처리 중인 문서 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="처리 중인 문서 목록 조회 중 오류가 발생했습니다.")

@router.get("/api/documents/check-document-status/{filename}")
async def check_document_status(filename: str) -> Dict[str, Any]:
    """
    특정 문서의 처리 상태를 확인합니다.
    """
    try:
        # 1. 처리 중인 문서 목록에서 확인
        if filename in processing_documents:
            status = processing_documents[filename]
            # 상위 상태는 최종 상태가 있으면 그것을, 없으면 현재 상태를 반영
            top_level_status = status.get("final_status") or status.get("status", "processing")
            return {
                "filename": filename,
                "status": top_level_status,
                "processing_status": status,
                "in_processing_list": True
            }
        
        # 2. 벡터 저장소에서 문서 존재 여부 확인
        try:
            # 파일명으로 벡터 저장소에서 검색
            search_results = document_service.search_documents(
                query="", 
                top_k=1, 
                filter_metadata={"filename": filename}
            )
            
            if search_results:
                return {
                    "filename": filename,
                    "status": "completed",
                    "in_vectorstore": True,
                    "chunk_count": len(search_results)
                }
        except Exception as e:
            logger.error(f"벡터 저장소 검색 실패: {e}")
        
        # 3. 파일 시스템에서 파일 존재 여부 확인
        file_path = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(file_path):
            return {
                "filename": filename,
                "status": "file_exists",
                "in_filesystem": True,
                "file_size": os.path.getsize(file_path)
            }
        
        return {
            "filename": filename,
            "status": "not_found",
            "message": "문서를 찾을 수 없습니다."
        }
        
    except Exception as e:
        logger.error(f"문서 상태 확인 실패: {e}")
        raise HTTPException(status_code=500, detail="문서 상태 확인 중 오류가 발생했습니다.")

@router.delete("/api/documents/{filename}")
async def delete_document(filename: str):
    """
    문서를 삭제합니다.
    """
    try:
        ensure_upload_dir()
        
        # 경로 순회 공격 방지
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="잘못된 파일명입니다.")
        
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
        
        if not os.path.isfile(file_path):
            raise HTTPException(status_code=400, detail="파일이 아닙니다.")
        
        # 벡터 저장소에서 해당 문서 삭제 시도
        deleted_count = 0
        vectorstore_deletion_success = True
        vectorstore_error = None
        
        try:
            # 파일명으로 직접 모든 관련 문서 삭제 (더 효율적)
            deleted_count = document_service.delete_documents_by_filename(filename)
            
            if deleted_count > 0:
                logger.info(f"벡터 저장소에서 총 {deleted_count}개 문서 청크가 삭제되었습니다.")
            else:
                logger.warning(f"파일명 '{filename}'에 해당하는 벡터 저장소 문서를 찾을 수 없습니다.")
                    
        except Exception as e:
            logger.error(f"벡터 저장소에서 문서 삭제 실패: {e}")
            vectorstore_deletion_success = False
            vectorstore_error = str(e)
        
        # 벡터스토어 삭제가 성공한 경우에만 파일 삭제
        if vectorstore_deletion_success:
            # 파일 삭제
            os.remove(file_path)
            logger.info(f"파일 삭제 완료: {filename}")
        else:
            # 벡터스토어 삭제 실패 시 파일은 유지
            logger.warning(f"벡터스토어 삭제 실패로 인해 파일 '{filename}'은 유지됩니다.")
            error_detail = f"벡터스토어에서 문서 삭제에 실패했습니다. 파일은 삭제되지 않았습니다."
            if vectorstore_error:
                error_detail += f" 오류: {vectorstore_error}"
            raise HTTPException(
                status_code=500, 
                detail=error_detail
            )
        
        # 처리 중인 문서 목록에서도 제거
        if filename in processing_documents:
            del processing_documents[filename]
        
        # RAG 문서 자동 재로드 (삭제 후 동기화)
        try:
            logger.info(f"문서 '{filename}' 삭제 후 RAG 자동 재로드 시작")
            rag_result = rag_service.reload_rag_documents()
            logger.info(f"RAG 자동 재로드 완료: {rag_result}")
        except Exception as e:
            logger.error(f"RAG 자동 재로드 실패: {e}")
        
        logger.info(f"문서 삭제 완료: {filename}")
        
        # 삭제 결과에 따른 메시지 생성
        if deleted_count > 0:
            message = f"문서가 성공적으로 삭제되었습니다. (벡터 저장소에서 {deleted_count}개 청크 삭제됨)"
        else:
            # 벡터 저장소에서 문서를 찾지 못한 경우, 처리 상태 확인
            if filename in processing_documents:
                message = "문서가 성공적으로 삭제되었습니다. (문서가 아직 처리 중이었습니다)"
            else:
                message = "문서가 성공적으로 삭제되었습니다. (벡터 저장소에서 해당 문서를 찾을 수 없었습니다)"
        
        return JSONResponse(
            status_code=200,
            content={
                "message": message,
                "filename": filename,
                "deleted_vector_chunks": deleted_count
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문서 삭제 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail="문서 삭제 중 오류가 발생했습니다.")



@router.get("/api/documents/{filename}/download")
async def download_document(filename: str):
    """
    문서를 다운로드합니다.
    """
    try:
        ensure_upload_dir()
        
        # 경로 순회 공격 방지
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="잘못된 파일명입니다.")
        
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
        
        if not os.path.isfile(file_path):
            raise HTTPException(status_code=400, detail="파일이 아닙니다.")
        
        from fastapi.responses import FileResponse
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문서 다운로드 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail="문서 다운로드 중 오류가 발생했습니다.")


@router.delete("/api/documents/dev/reset-all")
async def dev_reset_all_data():
    """
    개발자 모드 전용: 모든 업로드된 문서와 벡터 스토어 데이터를 완전히 초기화합니다.
    """
    try:
        ensure_upload_dir()
        
        # 1. 업로드된 모든 파일 삭제
        deleted_files = []
        for filename in os.listdir(UPLOAD_DIR):
            file_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    deleted_files.append(filename)
                    logger.info(f"파일 삭제 완료: {filename}")
                except Exception as e:
                    logger.error(f"파일 삭제 실패 {filename}: {e}")
        
        # 2. 벡터 저장소에서 모든 문서 삭제
        deleted_docs = 0
        try:
            # 모든 문서 조회
            all_documents = document_service.get_all_documents()
            
            for doc in all_documents:
                doc_id = doc.get("id")
                if doc_id and doc_id != "unknown":
                    if document_service.delete_document(doc_id):
                        deleted_docs += 1
                        logger.info(f"벡터 저장소에서 문서 삭제 완료: {doc_id}")
            
            logger.info(f"벡터 저장소에서 총 {deleted_docs}개 문서 삭제 완료")
            
        except Exception as e:
            logger.error(f"벡터 저장소 정리 중 오류: {e}")
        
        # 3. Chroma 벡터 저장소 캐시 데이터 완전 삭제
        cache_deleted = False
        try:
            # Chroma 벡터 저장소 디렉토리 삭제
            vectorstore_path = settings.chroma_persist_directory
            if os.path.exists(vectorstore_path):
                shutil.rmtree(vectorstore_path)
                logger.info(f"Chroma 벡터 저장소 캐시 삭제 완료: {vectorstore_path}")
                cache_deleted = True
            else:
                logger.info("삭제할 Chroma 벡터 저장소가 존재하지 않습니다.")
                
        except Exception as e:
            logger.error(f"Chroma 벡터 저장소 캐시 삭제 중 오류: {e}")
            # 캐시 삭제 실패해도 계속 진행
        
        # 4. 처리 중인 문서 목록 초기화
        processing_documents.clear()
        
        # 5. 벡터 저장소 재초기화 (캐시 삭제 후)
        vectorstore_reinitialized = False
        if cache_deleted:
            try:
                logger.info("벡터 저장소 재초기화 시작")
                document_service._initialize_vectorstore()
                vectorstore_reinitialized = True
                logger.info("벡터 저장소 재초기화 완료")
            except Exception as e:
                logger.error(f"벡터 저장소 재초기화 실패: {e}")
        
        # 6. RAG 서비스 재초기화
        try:
            logger.info("RAG 서비스 재초기화 시작")
            rag_result = rag_service.reload_rag_documents()
            logger.info(f"RAG 서비스 재초기화 완료: {rag_result}")
        except Exception as e:
            logger.error(f"RAG 서비스 재초기화 실패: {e}")
        
        logger.info(f"개발자 모드 전체 초기화 완료: {len(deleted_files)}개 파일, {deleted_docs}개 문서, 캐시 삭제: {cache_deleted}, 벡터저장소 재초기화: {vectorstore_reinitialized}")
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "개발자 모드: 모든 데이터가 성공적으로 초기화되었습니다.",
                "deleted_files": deleted_files,
                "deleted_files_count": len(deleted_files),
                "deleted_vector_documents": deleted_docs,
                "cache_deleted": cache_deleted,
                "vectorstore_reinitialized": vectorstore_reinitialized
            }
        )
        
    except Exception as e:
        error_msg = f"개발자 모드 전체 초기화 중 오류 발생: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/api/documents/dev/vectorstore-status")
async def get_vectorstore_status():
    """
    개발자 모드 전용: 벡터 스토어 상태 정보를 반환합니다.
    """
    try:
        # 문서 수 조회
        document_count = document_service.get_document_count()
        
        # 모든 문서 정보 조회
        all_documents = document_service.get_all_documents()
        
        # 파일 시스템의 업로드된 파일 수 조회
        upload_dir_files = []
        if os.path.exists(UPLOAD_DIR):
            for filename in os.listdir(UPLOAD_DIR):
                file_path = os.path.join(UPLOAD_DIR, filename)
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    upload_dir_files.append({
                        "filename": filename,
                        "size": file_size,
                        "size_mb": round(file_size / (1024 * 1024), 2)
                    })
        
        return JSONResponse(
            status_code=200,
            content={
                "vectorstore_status": document_service.get_vectorstore_status(),
                "document_count": document_count,
                "uploaded_files_count": len(upload_dir_files),
                "uploaded_files": upload_dir_files,
                "all_documents": all_documents
            }
        )
        
    except Exception as e:
        error_msg = f"벡터 스토어 상태 조회 중 오류 발생: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg) 