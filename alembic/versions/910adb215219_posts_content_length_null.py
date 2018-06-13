"""posts_content_length_null

Revision ID: 910adb215219
Revises: 60a859376b11
Create Date: 2018-06-13 21:14:28.341202

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '910adb215219'
down_revision = '60a859376b11'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('UPDATE posts SET content_length = 0 WHERE content_length IS NULL;')


def downgrade():
    pass
