from pathlib import Path
import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from .auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
    require_authority,
    require_citizen
)
from .database import get_db
from .models import User,Issue,IssueUpdate
from .schemas import (
    Token,
    UserLogin,
    UserRegister,
    UserResponse,
    IssueResponse,
    IssueStatusUpdate
)


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db),
):
    existing_user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    hashed_password = hash_password(
        user_data.password
    )

    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hashed_password,
        role="CITIZEN",
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post(
    "/login",
    response_model=Token,
)
def login(
    user_data: UserLogin,
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    if not verify_password(
        user_data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role,
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user

# -------------------------
# Issue Router
# -------------------------

issue_router = APIRouter(
    prefix="/api/issues",
    tags=["Issues"],
)


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


ALLOWED_CATEGORIES = {
    "POTHOLE",
    "ROAD_DAMAGE",
    "STREETLIGHT",
    "GARBAGE",
    "WATER_LEAK",
    "DRAINAGE",
    "ELECTRICAL_HAZARD",
    "OTHER",
}
# -------------------------
# Issue Routes
# -------------------------
@issue_router.post(
    "",
    response_model=IssueResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_issue(
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    image: UploadFile | None = File(None),

    current_user: User = Depends(require_citizen),
    db: Session = Depends(get_db),
):
    category = category.upper()

    if category not in ALLOWED_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid issue category",
        )

    image_url = None

    if image:
        extension = Path(image.filename).suffix
        filename = f"{uuid.uuid4()}{extension}"

        file_path = UPLOAD_DIR / filename

        with open(file_path, "wb") as buffer:
            buffer.write(image.file.read())

        image_url = f"/uploads/{filename}"

    new_issue = Issue(
        user_id=current_user.id,
        title=title,
        description=description,
        category=category,
        image_url=image_url,
        latitude=latitude,
        longitude=longitude,
        status="PENDING",
    )

    db.add(new_issue)
    db.commit()
    db.refresh(new_issue)

    return new_issue

@issue_router.get(
    "/my",
    response_model=list[IssueResponse],
)
def get_my_issues(
    current_user: User = Depends(require_citizen),
    db: Session = Depends(get_db),
):
    issues = (
        db.query(Issue)
        .filter(Issue.user_id == current_user.id)
        .order_by(Issue.created_at.desc())
        .all()
    )

    return issues

@issue_router.get(
    "/{issue_id}",
    response_model=IssueResponse,
)
def get_issue(
    issue_id: int,
    current_user: User = Depends(require_citizen),
    db: Session = Depends(get_db),
):
    issue = (
        db.query(Issue)
        .filter(
            Issue.id == issue_id,
            Issue.user_id == current_user.id,
        )
        .first()
    )

    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    return issue

# -------------------------
# Authority Router
# -------------------------

authority_router = APIRouter(
    prefix="/api/authority",
    tags=["Authority"],
)

# -------------------------
# Authority : Get All Issues
# -------------------------

@authority_router.get(
    "/issues",
    response_model=list[IssueResponse],
)
def get_all_issues(
    current_user: User = Depends(require_authority),
    db: Session = Depends(get_db),
):
    issues = (
        db.query(Issue)
        .order_by(Issue.created_at.desc())
        .all()
    )

    return issues

# -------------------------
# Authority : Claim Issues
# -------------------------

@issue_router.patch(
    "/{issue_id}/claim",
    response_model=IssueResponse,
)
def claim_issue(
    issue_id: int,
    current_user: User = Depends(require_authority),
    db: Session = Depends(get_db),
):
    issue = (
        db.query(Issue)
        .filter(Issue.id == issue_id)
        .first()
    )

    if issue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    if issue.assigned_to is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Issue is already assigned",
        )

    issue.assigned_to = current_user.id

    db.commit()
    db.refresh(issue)

    return issue

# -------------------------
# Authority : Update Issue Status
# -------------------------

@issue_router.patch(
    "/{issue_id}/status",
    response_model=IssueResponse,
)
def update_issue_status(
    issue_id: int,
    update_data: IssueStatusUpdate,
    current_user: User = Depends(require_authority),
    db: Session = Depends(get_db),
):
    issue = (
        db.query(Issue)
        .filter(Issue.id == issue_id)
        .first()
    )

    if issue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    # Only the assigned authority can update the issue
    if issue.assigned_to != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this issue",
        )

    allowed_statuses = {
        "PENDING",
        "IN_PROGRESS",
        "RESOLVED",
    }

    if update_data.status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status",
        )

    current_status = issue.status
    new_status = update_data.status

    valid_transitions = {
        "PENDING": ["IN_PROGRESS"],
        "IN_PROGRESS": ["RESOLVED"],
        "RESOLVED": [],
    }

    if new_status not in valid_transitions[current_status]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition: {current_status} -> {new_status}",
        )

    issue.status = new_status

    issue_update = IssueUpdate(
        issue_id=issue.id,
        updated_by=current_user.id,
        old_status=current_status,
        new_status=new_status,
        comment=update_data.comment,
    )

    db.add(issue_update)
    db.commit()
    db.refresh(issue)

    return issue
