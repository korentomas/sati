# PostgreSQL Database Visualization with pgAdmin

## Access pgAdmin

pgAdmin is now running and accessible at: **http://localhost:5050**

### Login Credentials:
- **Email:** admin@example.com
- **Password:** admin

## Connect to PostgreSQL Database

Once logged into pgAdmin, you'll need to add your PostgreSQL server:

1. Click on "Add New Server" or right-click on "Servers" → "Register" → "Server"

2. In the **General** tab:
   - Name: `SATI Database` (or any name you prefer)

3. In the **Connection** tab:
   - Host name/address: `db` (if connecting from within Docker network) or `localhost` (if connecting from your host)
   - Port: `5432`
   - Maintenance database: `satellite_imagery`
   - Username: `satellite_user`
   - Password: `satellite_pass`
   - Save password: Check this box for convenience

4. Click "Save"

## Alternative Connection Methods

### From Host Machine
If you prefer to use a desktop PostgreSQL client (like DBeaver, TablePlus, or pgAdmin desktop), use these connection details:
- Host: `localhost`
- Port: `5432`
- Database: `satellite_imagery`
- Username: `satellite_user`
- Password: `satellite_pass`

### Using psql Command Line
You can also connect directly via command line:
```bash
docker exec -it sati-db-1 psql -U satellite_user -d satellite_imagery
```

Or from your host machine if you have psql installed:
```bash
psql -h localhost -p 5432 -U satellite_user -d satellite_imagery
```

## Useful Docker Commands

View logs:
```bash
docker-compose logs pgadmin
```

Restart pgAdmin:
```bash
docker-compose restart pgadmin
```

Stop pgAdmin (database will remain running):
```bash
docker-compose stop pgadmin
```

Start pgAdmin again:
```bash
docker-compose start pgadmin
```

## Security Note
The current credentials are for development only. Make sure to change them for production use by updating the environment variables in docker-compose.yml.
