
Passwordless Authentication
===========================

Passwordless authentication for users is available via **Magic Links** and **One-Time Passwords (OTP)**. 

Overview
--------

- **Magic Link Flow**: Users receive single-use link via email that redirects them to the ``frontend_url/magiclink-activation/token=?<token>``.
- **OTP Flow**: Users receive a six-digit numeric code via email.

Magic Link Authentication
-------------------------

Request a Magic Link
~~~~~~~~~~~~~~~~~~~~

**Endpoint**: ``POST /myauth/passwordless/magic-link/request/``

**Request Body**:

.. code-block:: json

    {
        "email": "user@example.com"
    }

**Behavior**:

- If the email exists, generate a single-use token valid for 15 minutes.
- Send an email with a login link:
  
  ``<frontend_url>/magiclink-activation/?token=<token>``

- Deletes any existing magic links for this user.
- Response is always **200 OK**.

**Response**:

.. code-block:: json

    {
        "detail": "If an account exists, a link has been sent."
    }

Verify a Magic Link
~~~~~~~~~~~~~~~~~~~

**Endpoint**: ``POST /passwordless/magic-link/verify/``

**Request Body**:

.. code-block:: json

    {
        "token": "af051ac2e8..."
    }

**Behavior**:

- Validates token existence and expiration.
- Deletes the token after successful verification.
- Issues JWT access and refresh tokens.

**Response**:

.. code-block:: json

    {
        "refresh": "<jwt_refresh_token>",
        "access": "<jwt_access_token>"
    }


OTP Authentication
------------------

Request an OTP
~~~~~~~~~~~~~~

**Endpoint**: ``POST /myauth/passwordless/otp/request/``

**Request Body**:

.. code-block:: json

    {
        "email": "user@example.com"
    }

**Behavior**:

- If the email exists, generates a 6-digit OTP code with a definite lifetime, currently 15 minutes.
- OTP is hashed in the database.
- Sends OTP via email.
- Deletes any existing OTPs for this user.
- Response is always **200 OK**.

**Response**:

.. code-block:: json

    {
        "detail": "If an account exists, an OTP has been sent."
    }

Verify an OTP
~~~~~~~~~~~~

**Endpoint**: ``POST /auth/otp/verify/``

**Request Body**:

.. code-block:: json

    {
        "email": "user@example.com",
        "code": "123456"
    }

**Behavior**:

- Validates the OTP against the hashed secret.
- Deletes the OTP after use.
- Issues JWT access and refresh tokens.

**Response**:

.. code-block:: json

    {
        "refresh": "<jwt_refresh_token>",
        "access": "<jwt_access_token>"
    }


Security Considerations
-----------------------

- All tokens/codes are **single-use** and **expiring**.
- Responses for non-existent emails are **non-identifying**.
- Tokens/codes are deleted after use or on new requests.
- OTPs are stored **hashed**, and verification is constant-time to prevent timing attacks.
- Throttling is implemented per email to prevent abuse. Currently ``2 token/OTP requests`` and ``3 token/OTP verification requests`` are permited before the following response:

  .. code-block:: json

        {
            "detail": "Request was throttled. Expected available in 'n' seconds."
        }


