"""initial

Revision ID: 8c9e84f2d96d
Revises: 
Create Date: 2026-06-20 18:09:50.916379

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '8c9e84f2d96d'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('origins',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('title_ru', sa.String(), nullable=False),
    sa.Column('title_en', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('title_ru', 'title_en'),
    schema='animealarm'
    )
    op.create_table('users',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('joined_date', sa.Date(), nullable=False),
    sa.Column('is_admin', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    schema='animealarm'
    )
    op.create_table('voiceover_studios',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name'),
    schema='animealarm'
    )
    op.create_table('seasons',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('origin_id', sa.Integer(), nullable=False),
    sa.Column('title_ru', sa.String(), nullable=False),
    sa.Column('title_en', sa.String(), nullable=False),
    sa.Column('status', sa.Enum('RELEASED', 'ONGOING', 'ANNOUNCED', name='seasonstatus', schema="animealarm"), nullable=True),
    sa.Column('cover', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['origin_id'], ['animealarm.origins.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    schema='animealarm'
    )
    op.create_table('seasons_with_studio',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('season_id', sa.Integer(), nullable=False),
    sa.Column('studio_name', sa.String(), nullable=False),
    sa.Column('season_name', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['season_id'], ['animealarm.seasons.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['studio_name'], ['animealarm.voiceover_studios.name'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('season_id', 'studio_name'),
    schema='animealarm'
    )
    op.create_table('episodes',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('episode_number', sa.String(), nullable=False),
    sa.Column('season_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['season_id'], ['animealarm.seasons_with_studio.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('season_id', 'episode_number'),
    schema='animealarm'
    )
    op.create_table('season_studio_secondary',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('season_id', sa.Integer(), nullable=False),
    sa.Column('studio_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['season_id'], ['animealarm.seasons_with_studio.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['studio_id'], ['animealarm.voiceover_studios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    schema='animealarm'
    )
    op.create_table('user_season_secondary',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('season_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['season_id'], ['animealarm.seasons_with_studio.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['animealarm.users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'season_id'),
    schema='animealarm'
    )


def downgrade() -> None:
    op.drop_table('user_season_secondary', schema='animealarm')
    op.drop_table('season_studio_secondary', schema='animealarm')
    op.drop_table('episodes', schema='animealarm')
    op.drop_table('seasons_with_studio', schema='animealarm')
    op.drop_table('seasons', schema='animealarm')
    op.drop_table('voiceover_studios', schema='animealarm')
    op.drop_table('users', schema='animealarm')
    op.drop_table('origins', schema='animealarm')
