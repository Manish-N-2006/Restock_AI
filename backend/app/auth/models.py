from sqlalchemy import Column, Float, String, Text
from ..database import Base


class RevokedSession(Base):
    """Persisted revoked session JTIs so logout revocations survive container restarts."""

    __tablename__ = "revoked_sessions"

    jti = Column(String(128), primary_key=True, nullable=False)
    expires_at = Column(Float, nullable=False, index=True)
    revoked_at = Column(Float, nullable=False)


class LoginAttemptBucket(Base):
    """Persisted sliding-window failed-login attempt counters with bounded key count."""

    __tablename__ = "login_attempt_buckets"

    bucket_key = Column(String(128), primary_key=True, nullable=False)
    attempt_timestamps = Column(Text, nullable=False, default="[]")
    window_expires_at = Column(Float, nullable=False, index=True)
    updated_at = Column(Float, nullable=False, index=True)

