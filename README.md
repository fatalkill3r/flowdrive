# FlowDrive — Phase 4

FlowDrive is an operationally mature collaborative Django file manager with version history, notifications, audit logging, custom administration, storage analytics, and secure anonymous file requests.

## Requirements

- Python 3.10+
- SQLite (included with Python)

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

Open `http://127.0.0.1:8000` locally or `http://10.81.2.81:8000` from the network. The admin is available for operational use at `/admin/`, but is not the product interface.

## Optional demo data

```bash
python manage.py create_demo_data
```

This creates `demo` with password `FlowDriveDemo123!` and a sample folder hierarchy. Supply `--password` to choose another password.

## Configuration

All deployment-sensitive values are environment-driven; see `.env.example`. Uploaded bytes are stored beneath `FILEBOX_STORAGE_ROOT`, outside Django's publicly served static tree. The development quota is 10 GB and upload limit is 500 MB by default.

Duplicate active folder names are rejected case-insensitively within the same parent. The same name is allowed in different folders and after an item has been moved to Trash.

## Verification

```bash
python manage.py check
python manage.py test
```

## Architecture

- `apps/accounts`: authentication and per-user profile/quota counters
- `apps/files`: folder/file models, browser workflow, validation, storage service
- `apps/dashboard`: dashboard and central branding context
- `apps/activity`: extensible activity records
- `templates/components`: reusable navigation, modals, toasts and pagination
- `storage`: private UUID-based file bytes (never served as public media)

The storage service is the only layer responsible for physical file operations, keeping a future S3/MinIO/Azure adapter isolated from views and models.

Phase 3 adds centralized object permissions, direct file/folder grants, inherited folder access, Shared With Me/By Me, and public links with expiration, password, download, revocation, and regeneration controls.

Phase 4 adds retained file versions, restore/download controls, in-app notifications and preferences, an immutable audit trail, staff-only operational dashboards, quota management, upload requests, and cleanup commands.

Storage quota includes active current files, files in Trash, and all retained historical versions. Bytes are released only after permanent deletion or version pruning.

Operational commands:

```bash
python manage.py recalculate_storage
python manage.py cleanup_versions
python manage.py cleanup_trash
python manage.py cleanup_expired_links
```

## Permission and ownership policy

- Owners have full access and are the only users who can share, revoke access, create links, or permanently delete content.
- Viewers can browse and safely preview, but cannot download or modify.
- Downloaders add download access but cannot modify.
- Editors can upload, create folders, rename, and move items within the same shared tree. They cannot move content into private storage, reshare it, or delete owner content.
- The nearest explicit folder grant overrides inherited parent grants.
- Content created by an Editor inside a shared folder belongs to the folder owner and consumes the folder owner's quota. This intentionally keeps shared trees single-owner and destructive rules conservative.
