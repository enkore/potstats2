"""DailyStats remove active_threads

Revision ID: 979223d5d6db
Revises: 53dbc47c6c6a
Create Date: 2018-07-14 12:52:10.206258

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '979223d5d6db'
down_revision = '53dbc47c6c6a'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('baked_daily_stats', 'active_threads')


def downgrade():
    op.add_column('baked_daily_stats', sa.Column('active_threads', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True))
