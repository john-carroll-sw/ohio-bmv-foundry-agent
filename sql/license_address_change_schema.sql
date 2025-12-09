-- Ohio BMV Demo Database Schema
-- License Address Change Requests Table

-- This table stores driver's license address change requests
-- submitted through the AI agent via the MCP tool.

CREATE TABLE dbo.LicenseAddressChangeRequests (
    -- Primary key and audit fields
    Id                     INT IDENTITY(1,1) PRIMARY KEY,
    CreatedAt              DATETIME2      NOT NULL DEFAULT SYSUTCDATETIME(),
    
    -- Driver information
    DriverLicenseNumber    NVARCHAR(50)   NOT NULL,
    DateOfBirth            DATE           NOT NULL,
    FirstName              NVARCHAR(100)  NOT NULL,
    MiddleName             NVARCHAR(100)  NULL,
    LastName               NVARCHAR(100)  NOT NULL,
    
    -- Contact information
    Email                  NVARCHAR(255)  NULL,
    Phone                  NVARCHAR(50)   NULL,
    
    -- Previous address
    OldAddressLine1        NVARCHAR(255)  NOT NULL,
    OldAddressLine2        NVARCHAR(255)  NULL,
    OldCity                NVARCHAR(100)  NOT NULL,
    OldState               NVARCHAR(50)   NOT NULL,
    OldZip                 NVARCHAR(50)   NOT NULL,
    
    -- New address
    NewAddressLine1        NVARCHAR(255)  NOT NULL,
    NewAddressLine2        NVARCHAR(255)  NULL,
    NewCity                NVARCHAR(100)  NOT NULL,
    NewState               NVARCHAR(50)   NOT NULL,
    NewZip                 NVARCHAR(50)   NOT NULL,
    
    -- Additional metadata
    PreferredContactMethod NVARCHAR(50)   NULL,     -- 'email', 'phone', or 'mail'
    ConversationSummary    NVARCHAR(MAX)  NULL      -- Short audit summary from the agent
);

-- Indexes for common queries
CREATE INDEX IX_LicenseAddressChange_CreatedAt 
    ON dbo.LicenseAddressChangeRequests(CreatedAt DESC);

CREATE INDEX IX_LicenseAddressChange_DriverLicenseNumber 
    ON dbo.LicenseAddressChangeRequests(DriverLicenseNumber);

-- Example: Query to view recent requests
-- SELECT TOP 10 * 
-- FROM dbo.LicenseAddressChangeRequests 
-- ORDER BY CreatedAt DESC;

-- Example: Query to find requests for a specific license
-- SELECT * 
-- FROM dbo.LicenseAddressChangeRequests 
-- WHERE DriverLicenseNumber = 'OH12345678' 
-- ORDER BY CreatedAt DESC;
