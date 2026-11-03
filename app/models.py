"""Database models.

The schema intentionally follows webstack-go's six tables so the existing admin
frontend and API contracts continue to work.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )


class Category(TimestampMixin, Base):
    __tablename__ = "st_category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    title: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    icon: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Site(TimestampMixin, Base):
    __tablename__ = "st_site"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    icon: Mapped[str] = mapped_column(Text, default="", nullable=False)
    description: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    url: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class SysConfig(Base):
    __tablename__ = "sys_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    about_site: Mapped[str] = mapped_column(Text, default="", nullable=False)
    about_author: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_about: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_search: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    site_title: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    site_keyword: Mapped[str] = mapped_column(Text, default="", nullable=False)
    site_desc: Mapped[str] = mapped_column(Text, default="", nullable=False)
    site_record: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    site_logo: Mapped[str] = mapped_column(Text, default="", nullable=False)
    site_favicon: Mapped[str] = mapped_column(Text, default="", nullable=False)
    site_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)


class User(TimestampMixin, Base):
    __tablename__ = "sys_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(100), nullable=False)


class Menu(TimestampMixin, Base):
    __tablename__ = "sys_menu"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pid: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    link: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    icon: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class UserMenu(TimestampMixin, Base):
    __tablename__ = "sys_user_menu"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    menu_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
