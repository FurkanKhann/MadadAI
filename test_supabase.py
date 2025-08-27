from config import supabase

# Insert test company
data = supabase.table("companies").insert({
    "company_name": "Master Blaster Inc",
    "email": "info@masterblaster.com",
    "phone": "212-555-1234",
    "address": "101 Thunderdome Road, Bartertown"
}).execute()

print(data)
