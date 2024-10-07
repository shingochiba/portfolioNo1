"""Added status and due_date columns

Revision ID: 977896353767
Revises: 
Create Date: 2024-10-04 21:29:39.490611

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '977896353767'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 既に `due_date` が存在するため、この行をコメントアウトまたは削除
    # op.add_column('task', sa.Column('due_date', sa.Date(), nullable=True))
    pass  # これで何も実行しないようにします

def downgrade():
    # `due_date` カラムを削除する必要がない場合、この行も削除
    # op.drop_column('task', 'due_date')
    pass
