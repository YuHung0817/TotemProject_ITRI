from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.db.session import get_db
from app.schemas.chat import ChatroomSnapshot, ChatroomUpdate
from app.services.chat_service import (
    chatroom_snapshot,
    delete_chatroom,
    list_chatrooms,
    rename_chatroom,
    sync_chatroom,
)

router = APIRouter(prefix="/chatrooms")


@router.get("", response_model=list[ChatroomSnapshot])
def get_chatrooms(
    user: CurrentUser, db: Session = Depends(get_db)
) -> list[ChatroomSnapshot]:
    return list_chatrooms(db, user.id)


@router.get("/{chatroom_id}", response_model=ChatroomSnapshot)
def get_chatroom(
    chatroom_id: str, user: CurrentUser, db: Session = Depends(get_db)
) -> ChatroomSnapshot:
    return chatroom_snapshot(db, chatroom_id, user.id)


@router.put("/{chatroom_id}", response_model=ChatroomSnapshot)
def put_chatroom(
    chatroom_id: str,
    snapshot: ChatroomSnapshot,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> ChatroomSnapshot:
    if snapshot.id != chatroom_id:
        from fastapi import HTTPException

        raise HTTPException(422, "Chatroom id does not match request path")
    return sync_chatroom(db, snapshot, user.id)


@router.patch("/{chatroom_id}", response_model=ChatroomSnapshot)
def patch_chatroom(
    chatroom_id: str,
    request: ChatroomUpdate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> ChatroomSnapshot:
    return rename_chatroom(db, chatroom_id, request.title, user.id)


@router.delete("/{chatroom_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_chatroom(
    chatroom_id: str, user: CurrentUser, db: Session = Depends(get_db)
) -> Response:
    delete_chatroom(db, chatroom_id, user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
