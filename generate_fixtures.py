"""
Script untuk convert JSON biasa ke Django Fixtures format
Usage: python generate_fixtures.py input.json output.json
"""

import json
import sys
import uuid
from django.contrib.auth.hashers import make_password

def generate_user_fixtures(users_data):
    """Convert users data ke Django fixtures format"""
    fixtures = []
    
    for user_data in users_data:
        user_id = str(uuid.uuid4())
        fixture = {
            "model": "Auth_Profile.user",
            "pk": user_id,
            "fields": {
                "nama": user_data.get("nama", ""),
                "email": user_data.get("email", ""),
                "kelamin": user_data.get("kelamin", "L"),
                "tanggal_lahir": user_data.get("tanggal_lahir", "2000-01-01"),
                "nomor_handphone": user_data.get("nomor_handphone", ""),
                "password": make_password(user_data.get("password", "password123"))
            }
        }
        fixtures.append(fixture)
    
    return fixtures

def generate_post_fixtures(posts_data, user_email_to_id):
    """Convert posts data ke Django fixtures format"""
    fixtures = []
    
    for post_data in posts_data:
        post_id = str(uuid.uuid4())
        creator_email = post_data.get("creator_email")
        
        if creator_email not in user_email_to_id:
            print(f"Warning: Creator {creator_email} not found, skipping post: {post_data.get('title')}")
            continue
        
        fixture = {
            "model": "Sport_Partner.partnerpost",
            "pk": post_id,
            "fields": {
                "creator": user_email_to_id[creator_email],
                "title": post_data.get("title", ""),
                "description": post_data.get("description", ""),
                "category": post_data.get("category", "soccer"),
                "tanggal": post_data.get("tanggal", "2025-01-01"),
                "jam_mulai": post_data.get("jam_mulai", "09:00:00"),
                "jam_selesai": post_data.get("jam_selesai", "11:00:00"),
                "lokasi": post_data.get("lokasi", "")
            }
        }
        fixtures.append(fixture)
    
    return fixtures

def convert_to_fixtures(input_file, output_file):
    """Main function untuk convert JSON ke fixtures"""
    
    # Load input JSON
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    all_fixtures = []
    user_email_to_id = {}
    
    # Generate user fixtures
    if 'users' in data:
        user_fixtures = generate_user_fixtures(data['users'])
        
        # Map email to UUID untuk reference di posts
        for i, user_data in enumerate(data['users']):
            email = user_data.get('email')
            if email:
                user_email_to_id[email] = user_fixtures[i]['pk']
        
        all_fixtures.extend(user_fixtures)
        print(f"✓ Generated {len(user_fixtures)} user fixtures")
    
    # Generate post fixtures
    if 'posts' in data:
        post_fixtures = generate_post_fixtures(data['posts'], user_email_to_id)
        all_fixtures.extend(post_fixtures)
        print(f"✓ Generated {len(post_fixtures)} post fixtures")
    
    # Save to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_fixtures, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Fixtures saved to: {output_file}")
    print(f"Total: {len(all_fixtures)} fixtures")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python generate_fixtures.py input.json output.json")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    convert_to_fixtures(input_file, output_file)