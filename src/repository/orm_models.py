from datetime import date
from typing import Optional
from uuid import uuid4, UUID
from enum import Enum

from sqlalchemy import MetaData, Date, Text, UniqueConstraint, ForeignKey, BigInteger
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship


class SeasonStatus(str, Enum):
    RELEASED = 'released'
    ONGOING = 'ongoing'
    ANNOUNCED = 'announced'


class Base(DeclarativeBase):
    metadata = MetaData()
    type_annotation_map = {}


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True)
    joined_date: Mapped[date] = mapped_column(default=date.today)
    is_admin: Mapped[bool | None] = mapped_column(default=False)
    animelist: Mapped[list['DubbedSeason']] = relationship(
        back_populates='followers',
        secondary='user_season_secondary',
        lazy='selectin'
    )

    def subscribe(self, season: 'DubbedSeason'):
        self.animelist.append(season)

    def is_subsribed(self, season: 'DubbedSeason'):
        return season in self.animelist

    def unsubscribe(self, season: 'DubbedSeason'):
        self.animelist.remove(season)

    def unsubscribe_all(self):
        self.animelist.clear()


class Origin(Base):
    __tablename__ = 'origins'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title_ru: Mapped[str]
    title_en: Mapped[str]
    seasons: Mapped[list['Season']] = relationship(back_populates='origin')

    __table_args__ = (
        UniqueConstraint('title_ru', 'title_en'),
    )


class Season(Base):
    __tablename__ = 'seasons'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    origin_id: Mapped[int] = mapped_column(ForeignKey('origins.id', ondelete='CASCADE'))
    title_ru: Mapped[str]
    title_en: Mapped[str]
    status: Mapped[Optional['SeasonStatus']] = mapped_column(default=SeasonStatus.ONGOING)
    cover: Mapped[str | None]

    origin: Mapped['Origin'] = relationship(back_populates='seasons')
    involved_studios: Mapped[list['DubbedSeason']] = relationship(back_populates='season')


class DubbedSeason(Base):
    __tablename__ = 'seasons_with_studio'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    season_id: Mapped[int] = mapped_column(ForeignKey('seasons.id', ondelete='CASCADE'))
    studio_name: Mapped[int] = mapped_column(ForeignKey('voiceover_studios.name', ondelete='CASCADE'))
    # for denormolization
    season_name: Mapped[str]

    season: Mapped['Season'] = relationship(back_populates='involved_studios')
    episodes: Mapped[list['Episode']] = relationship(back_populates='season')
    studio: Mapped['VoiceoverStudio'] = relationship(back_populates='work_with_seasons', secondary='season_studio_secondary')
    followers: Mapped[list['User']] = relationship(back_populates='animelist', secondary='user_season_secondary')

    __table_args__ = (
        UniqueConstraint('season_id', 'studio_name'),
    )


class Episode(Base):
    __tablename__ = 'episodes'

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str | None]
    episode_number: Mapped[int]

    season_id: Mapped[int] = mapped_column(ForeignKey('seasons_with_studio.id', ondelete='CASCADE'))
    season: Mapped['DubbedSeason'] = relationship(back_populates='episodes')

    __table_args__ = (
        UniqueConstraint('season_id', 'episode_number'),
    )


class VoiceoverStudio(Base):
    __tablename__ = 'voiceover_studios'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str]

    work_with_seasons: Mapped[list['DubbedSeason']] = relationship(
        back_populates='studio', 
        secondary='season_studio_secondary'
    )

    __table_args__ = (
        UniqueConstraint('name'),
    )


class UserSeasonSecondary(Base):
    __tablename__ = 'user_season_secondary'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    season_id: Mapped[int] = mapped_column(ForeignKey('seasons_with_studio.id', ondelete='CASCADE'))

    __table_args__ = (
        UniqueConstraint('user_id', 'season_id'),
    )


class SeasonStudioSecondary(Base):
    __tablename__ = 'season_studio_secondary'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    season_id: Mapped[int] = mapped_column(ForeignKey('seasons_with_studio.id', ondelete='CASCADE'))
    studio_id: Mapped[int] = mapped_column(ForeignKey('voiceover_studios.id', ondelete='CASCADE'))
