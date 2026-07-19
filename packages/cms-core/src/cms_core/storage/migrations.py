"""Ordered schema migrations shared by all SQL backends.

The scripts are ANSI SQL (CREATE TABLE / ALTER TABLE ADD COLUMN) so every
engine applies the same history; each backend only differs in how it tracks
the applied version (SQLite: ``user_version``; PostgreSQL: a
``schema_migrations`` table).
"""

MIGRATIONS: tuple[str, ...] = (
    """
    CREATE TABLE articles (
        id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        title TEXT NOT NULL,
        summary TEXT NOT NULL,
        body_markdown TEXT NOT NULL
    );
    CREATE TABLE translations (
        article_id TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
        language TEXT NOT NULL,
        title TEXT NOT NULL,
        summary TEXT NOT NULL,
        body_markdown TEXT NOT NULL,
        source_checksum TEXT NOT NULL,
        PRIMARY KEY (article_id, language)
    );
    """,
    """
    CREATE TABLE pages (
        id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        slug TEXT NOT NULL
    );
    CREATE TABLE page_translations (
        page_id TEXT NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
        language TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        slug TEXT NOT NULL,
        source_checksum TEXT NOT NULL,
        PRIMARY KEY (page_id, language)
    );
    CREATE TABLE sections (
        page_id TEXT NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
        key TEXT NOT NULL,
        position INTEGER NOT NULL,
        kind TEXT NOT NULL,
        fields_json TEXT NOT NULL,
        media_json TEXT NOT NULL,
        PRIMARY KEY (page_id, key)
    );
    CREATE TABLE section_translations (
        page_id TEXT NOT NULL,
        section_key TEXT NOT NULL,
        language TEXT NOT NULL,
        fields_json TEXT NOT NULL,
        media_json TEXT NOT NULL,
        source_checksum TEXT NOT NULL,
        PRIMARY KEY (page_id, section_key, language),
        FOREIGN KEY (page_id, section_key)
            REFERENCES sections(page_id, key) ON DELETE CASCADE
    );
    CREATE TABLE media_assets (
        id TEXT PRIMARY KEY,
        path TEXT NOT NULL,
        mime_type TEXT NOT NULL,
        width INTEGER,
        height INTEGER
    );
    CREATE TABLE media_alt_texts (
        media_id TEXT NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
        language TEXT NOT NULL,
        alt TEXT NOT NULL,
        PRIMARY KEY (media_id, language)
    );
    """,
    """
    ALTER TABLE articles ADD COLUMN slug TEXT;
    ALTER TABLE translations ADD COLUMN slug TEXT;
    """,
    """
    ALTER TABLE articles ADD COLUMN category TEXT;
    ALTER TABLE articles ADD COLUMN tags_json TEXT NOT NULL DEFAULT '[]';
    """,
    """
    ALTER TABLE articles ADD COLUMN cover TEXT;
    """,
    """
    CREATE TABLE users (
        username TEXT PRIMARY KEY,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE admin_sessions (
        token_hash TEXT PRIMARY KEY,
        username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
        csrf_token TEXT NOT NULL,
        expires_at TEXT NOT NULL
    );
    """,
    """
    ALTER TABLE users ADD COLUMN language TEXT;
    """,
    """
    ALTER TABLE articles ADD COLUMN publish_at TEXT;
    ALTER TABLE pages ADD COLUMN publish_at TEXT;
    """,
    """
    CREATE TABLE revisions (
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        revision INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        author TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        PRIMARY KEY (entity_type, entity_id, revision)
    );
    """,
    """
    ALTER TABLE articles ADD COLUMN deleted_at TEXT;
    ALTER TABLE pages ADD COLUMN deleted_at TEXT;
    """,
)
