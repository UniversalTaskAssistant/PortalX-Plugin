## Output File Structure

```
Output/
├── websites/             # Website data (shared across users)
│   ├── company1/
│   │   ├── raw/          # Raw crawled HTML
│   │   ├── processed/    # Processed text documents
│   │   └── embeddings/   # Vector embeddings
│   └── company2/
│       ├── raw/
│       ├── processed/
│       └── embeddings/
│
└── users/                # User-specific data
    ├── user1/
    │   └── chats/
    │       ├── conversation1.json
    │       └── conversation2.json
    └── user2/
        └── chats/
            ├── conversation1.json
            └── conversation2.json
```
