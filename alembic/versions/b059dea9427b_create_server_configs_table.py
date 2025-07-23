"""create_server_configs_table

Revision ID: b059dea9427b
Revises: 60012a39537d
Create Date: 2025-07-23 10:39:26.020587

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b059dea9427b'
down_revision: Union[str, Sequence[str], None] = '60012a39537d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_configs テーブルを作成
    op.create_table(
        'server_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('guild_id', sa.BigInteger(), nullable=False),
        sa.Column('default_area_code', sa.String(10), nullable=True),
        sa.Column('default_area_name', sa.String(100), nullable=True),
        sa.Column('admin_channel_id', sa.BigInteger(), nullable=True),
        sa.Column('is_weather_enabled', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_ai_enabled', sa.Boolean(), nullable=True, default=True),
        sa.Column('max_forecast_days', sa.Integer(), nullable=True, default=7),
        sa.Column('timezone', sa.String(50), nullable=True, default='Asia/Tokyo'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # インデックスを作成
    op.create_index('ix_server_configs_guild_id', 'server_configs', ['guild_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    # インデックスを削除
    op.drop_index('ix_server_configs_guild_id', table_name='server_configs')
    
    # テーブルを削除
    op.drop_table('server_configs')
