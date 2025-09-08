Multi-tenant API Overview
========================

This project uses a multi-tenant setup with **Companies** (parent entities) 
and **Organizations** (child entities). A user can be:

- **Company owner** → owns a company, can edit its details.
- **Organization member/admin/owner** → belongs to one or more organizations under a company.
- **Staff (is_staff=True)** → superuser-like access, can see all companies and organizations.

Vital Endpoints
--------------

**/company/**
~~~~~~~~~~~~
- For *regular users*: returns all companies owned by the requesting user.
- For *staff users*: returns all companies in the system.

Response Example::

    [
        {
            "id": "dd00c54e-610b-463e-b49f-888e57865146",
            "name": "comp2",
            "theme": "default",
            "created_at": "2025-08-20T10:11:58.581325Z",
            "updated_at": "2025-09-08T13:15:51.947985Z",
            "owner": "bf95540c-1108-4637-8d5e-1b3162396c8a"
        }
    ]


**/organization/**
~~~~~~~~~~~~~~~~~~
- For *regular users*: returns all organizations where the user is a member, 
  including their `role` (member, admin, owner).
- For *staff users*: returns all organizations across all companies.

Response Example::

    [
        {
            "id": "org-123",
            "name": "Org A",
            "company_name": "Acme Inc",
            "role": "admin",
            "created_at": "2025-09-08T15:44:50.257Z",
            "updated_at": "2025-09-08T15:44:50.257Z"
        },
        {
            "id": "org-456",
            "name": "Org B",
            "company_name": "Acme Inc",
            "role": "member",
            "created_at": "2025-09-08T15:44:50.257Z",
            "updated_at": "2025-09-08T15:44:50.257Z"
        }
    ]


**/organization/{id}/company/**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Returns the company details for the given organization.
- Includes an `is_owner` flag so the frontend knows if the user 
  can edit the company details.

Response Example::

    {
        "id": "dd00c54e-610b-463e-b49f-888e57865146",
        "name": "comp2",
        "theme": "default",
        "created_at": "2025-08-20T10:11:58.581325Z",
        "updated_at": "2025-09-08T13:15:51.947985Z",
        "owner": "bf95540c-1108-4637-8d5e-1b3162396c8a",
        "is_owner": false
    }


Frontend Usage Flow
-------------------
1. After login, **fetch organizations** for the signed-in user from ``/organization/``.
   - This gives the list of orgs the user belongs to, along with roles.

2. If the user navigates to a **company detail page**, fetch their company data:
   - Use ``/company/`` to get companies they *own* (regular users) or all companies (staff).
   - Or use ``/organization/{id}/company/`` to fetch the parent company for a specific org.

3. Company and organization data are **independent**, except that an organization always belongs to one company.



.. mermaid::

   sequenceDiagram
       participant U as User
       participant FE as Frontend App
       participant API as Backend API

       U->>FE: Login with credentials
       FE->>API: POST /auth/login
       API-->>FE: 200 OK + JWT/Session

       Note over FE: After login, fetch orgs

       FE->>API: GET /organization/
       API-->>FE: List of organizations (with role & company_name)

       alt User navigates to company detail page
           FE->>API: GET /organization/{id}/company/
           API-->>FE: Company details + is_owner flag
       end

