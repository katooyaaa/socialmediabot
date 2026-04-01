import asyncpg
from typing import Optional, List


class Database:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        fixed_dsn = self.dsn

        if fixed_dsn.startswith("postgresql+asyncpg://"):
            fixed_dsn = fixed_dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
        elif fixed_dsn.startswith("postgres+asyncpg://"):
            fixed_dsn = fixed_dsn.replace("postgres+asyncpg://", "postgres://", 1)

        self.pool = await asyncpg.create_pool(
            dsn=fixed_dsn,
            min_size=1,
            max_size=1,
            command_timeout=60
        )

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def create_tables(self):
        async with self.pool.acquire() as con:
            await con.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT NOT NULL,
                    owner_id BIGINT NOT NULL,
                    name TEXT NOT NULL,
                    avatar_url TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(guild_id, name)
                );
            """)

            await con.execute("""
                CREATE TABLE IF NOT EXISTS selected_accounts (
                    guild_id BIGINT NOT NULL,
                    user_id BIGINT NOT NULL,
                    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                    PRIMARY KEY (guild_id, user_id)
                );
            """)

            await con.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT NOT NULL,
                    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                    author_user_id BIGINT NOT NULL,
                    channel_id BIGINT NOT NULL,
                    message_id BIGINT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    image_url TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

            await con.execute("""
                CREATE TABLE IF NOT EXISTS post_likes (
                    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                    user_id BIGINT NOT NULL,
                    PRIMARY KEY (post_id, user_id)
                );
            """)

            # NEU: Dislikes
            await con.execute("""
                CREATE TABLE IF NOT EXISTS post_dislikes (
                    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                    user_id BIGINT NOT NULL,
                    PRIMARY KEY (post_id, user_id)
                );
            """)

    async def create_account(self, guild_id: int, owner_id: int, name: str, avatar_url: str):
        async with self.pool.acquire() as con:
            return await con.fetchrow("""
                INSERT INTO accounts (guild_id, owner_id, name, avatar_url)
                VALUES ($1, $2, $3, $4)
                RETURNING *;
            """, guild_id, owner_id, name, avatar_url)

    async def get_account_by_name(self, guild_id: int, name: str):
        async with self.pool.acquire() as con:
            return await con.fetchrow("""
                SELECT * FROM accounts
                WHERE guild_id = $1 AND LOWER(name) = LOWER($2);
            """, guild_id, name)

    async def get_all_accounts_with_likes(self, guild_id: int) -> List[asyncpg.Record]:
        async with self.pool.acquire() as con:
            return await con.fetch("""
                SELECT
                    a.id,
                    a.name,
                    a.owner_id,
                    a.avatar_url,
                    COUNT(DISTINCT pl.user_id)::INT AS likes,
                    COUNT(DISTINCT pd.user_id)::INT AS dislikes
                FROM accounts a
                LEFT JOIN posts p ON p.account_id = a.id
                LEFT JOIN post_likes pl ON pl.post_id = p.id
                LEFT JOIN post_dislikes pd ON pd.post_id = p.id
                WHERE a.guild_id = $1
                GROUP BY a.id
                ORDER BY likes DESC, a.name ASC;
            """, guild_id)

    async def get_accounts_by_owner_with_likes(self, guild_id: int, owner_id: int):
        async with self.pool.acquire() as con:
            return await con.fetch("""
                SELECT
                    a.id,
                    a.name,
                    a.owner_id,
                    a.avatar_url,
                    COUNT(DISTINCT pl.user_id)::INT AS likes,
                    COUNT(DISTINCT pd.user_id)::INT AS dislikes
                FROM accounts a
                LEFT JOIN posts p ON p.account_id = a.id
                LEFT JOIN post_likes pl ON pl.post_id = p.id
                LEFT JOIN post_dislikes pd ON pd.post_id = p.id
                WHERE a.guild_id = $1
                  AND a.owner_id = $2
                GROUP BY a.id
                ORDER BY likes DESC, a.name ASC;
            """, guild_id, owner_id)

    async def select_account(self, guild_id: int, user_id: int, account_id: int):
        async with self.pool.acquire() as con:
            await con.execute("""
                INSERT INTO selected_accounts (guild_id, user_id, account_id)
                VALUES ($1, $2, $3)
                ON CONFLICT (guild_id, user_id)
                DO UPDATE SET account_id = EXCLUDED.account_id;
            """, guild_id, user_id, account_id)

    async def get_selected_account(self, guild_id: int, user_id: int):
        async with self.pool.acquire() as con:
            return await con.fetchrow("""
                SELECT a.*
                FROM selected_accounts sa
                JOIN accounts a ON a.id = sa.account_id
                WHERE sa.guild_id = $1 AND sa.user_id = $2;
            """, guild_id, user_id)

    async def delete_account(self, guild_id: int, owner_id: int, name: str):
        async with self.pool.acquire() as con:
            return await con.fetchrow("""
                DELETE FROM accounts
                WHERE guild_id = $1
                  AND owner_id = $2
                  AND LOWER(name) = LOWER($3)
                RETURNING *;
            """, guild_id, owner_id, name)

    async def create_post(
        self,
        guild_id: int,
        account_id: int,
        author_user_id: int,
        channel_id: int,
        message_id: int,
        title: str,
        image_url: Optional[str]
    ):
        async with self.pool.acquire() as con:
            return await con.fetchrow("""
                INSERT INTO posts (
                    guild_id,
                    account_id,
                    author_user_id,
                    channel_id,
                    message_id,
                    title,
                    image_url
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING *;
            """, guild_id, account_id, author_user_id, channel_id, message_id, title, image_url)

    async def get_post_by_message_id(self, message_id: int):
        async with self.pool.acquire() as con:
            return await con.fetchrow("""
                SELECT * FROM posts
                WHERE message_id = $1;
            """, message_id)

    async def like_post(self, message_id: int, user_id: int):
        async with self.pool.acquire() as con:
            post = await con.fetchrow("""
                SELECT id FROM posts WHERE message_id = $1;
            """, message_id)

            if not post:
                return

            await con.execute("""
                INSERT INTO post_likes (post_id, user_id)
                VALUES ($1, $2)
                ON CONFLICT (post_id, user_id) DO NOTHING;
            """, post["id"], user_id)

    async def unlike_post(self, message_id: int, user_id: int):
        async with self.pool.acquire() as con:
            post = await con.fetchrow("""
                SELECT id FROM posts WHERE message_id = $1;
            """, message_id)

            if not post:
                return

            await con.execute("""
                DELETE FROM post_likes
                WHERE post_id = $1 AND user_id = $2;
            """, post["id"], user_id)

    async def dislike_post(self, message_id: int, user_id: int):
        async with self.pool.acquire() as con:
            post = await con.fetchrow("""
                SELECT id FROM posts WHERE message_id = $1;
            """, message_id)

            if not post:
                return

            await con.execute("""
                INSERT INTO post_dislikes (post_id, user_id)
                VALUES ($1, $2)
                ON CONFLICT (post_id, user_id) DO NOTHING;
            """, post["id"], user_id)

    async def undislike_post(self, message_id: int, user_id: int):
        async with self.pool.acquire() as con:
            post = await con.fetchrow("""
                SELECT id FROM posts WHERE message_id = $1;
            """, message_id)

            if not post:
                return

            await con.execute("""
                DELETE FROM post_dislikes
                WHERE post_id = $1 AND user_id = $2;
            """, post["id"], user_id)

    async def get_post_like_count(self, post_id: int) -> int:
        async with self.pool.acquire() as con:
            return await con.fetchval("""
                SELECT COUNT(*)::INT
                FROM post_likes
                WHERE post_id = $1;
            """, post_id) or 0

    # Optional
    async def get_post_dislike_count(self, post_id: int) -> int:
        async with self.pool.acquire() as con:
            return await con.fetchval("""
                SELECT COUNT(*)::INT
                FROM post_dislikes
                WHERE post_id = $1;
            """, post_id) or 0