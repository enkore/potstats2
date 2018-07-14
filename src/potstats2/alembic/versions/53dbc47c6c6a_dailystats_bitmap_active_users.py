"""DailyStats bitmap active_users

Revision ID: 53dbc47c6c6a
Revises: ed9b3bff8adc
Create Date: 2018-07-14 12:30:58.359802

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.

revision = '53dbc47c6c6a'
down_revision = 'ed9b3bff8adc'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('baked_daily_stats', 'active_users')
    op.add_column('baked_daily_stats', sa.Column('active_users', sa.Binary(), nullable=True))    # ### end Alembic commands ###


def downgrade():
    op.drop_column('baked_daily_stats', 'active_users')
    op.add_column('baked_daily_stats', sa.Column('active_users', JSONB(), nullable=True))