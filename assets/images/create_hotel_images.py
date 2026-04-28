
#!/usr/bin/env python3
import os
from PIL import Image, ImageDraw, ImageFont
import requests

# Hotel image names from the seeder
hotel_images = [
    'oberoi_mumbai.jpg', 'taj_hyderabad.jpg', 'leela_chennai.jpg', 'hyatt_goa.jpg',
    'ritz_bangalore.jpg', 'jw_mumbai.jpg', 'stregis_mumbai.jpg', 'leela_delhi.jpg',
    'taj_udaipur.jpg', 'itc_mumbai.jpg', 'itc_delhi.jpg', 'conrad_bangalore.jpg',
    'westin_pune.jpg', 'marriott_jaipur.jpg', 'park_kolkata.jpg', 'vivanta_kochi.jpg',
    'hyatt_delhi.jpg', 'radisson_goa.jpg', 'sheraton_chennai.jpg', 'crowne_kochi.jpg',
    'holiday_mumbai.jpg', 'novotel_hyderabad.jpg', 'doubletree_goa.jpg', 'fourpoints_pune.jpg',
    'aloft_bangalore.jpg', 'lemontree_delhi.jpg', 'ginger_mumbai.jpg', 'redfox_jaipur.jpg',
    'ibis_chennai.jpg', 'keys_bangalore.jpg', 'fab_kolkata.jpg', 'treebo_hyderabad.jpg',
    'zone_pune.jpg', 'sterling_goa.jpg', 'country_kochi.jpg', 'clarks_agra.jpg',
    'gateway_gangtok.jpg', 'highlands_shimla.jpg', 'oyo_delhi.jpg', 'decent_mumbai.jpg',
    'royal_chennai.jpg', 'bluediamond_bangalore.jpg', 'grand_kolkata.jpg', 'backwater_kochi.jpg',
    'paradise_goa.jpg', 'pinkcity_jaipur.jpg', 'skylark_pune.jpg', 'deccan_hyderabad.jpg',
    'srinagar_kashmir.jpg', 'hillview_manali.jpg', 'beach_pondicherry.jpg', 'heritage_jodhpur.jpg',
    'riverside_rishikesh.jpg'
]

def create_hotel_placeholder(filename, hotel_name):
    """Create a placeholder hotel image"""
    # Create a 400x300 image with gradient background
    img = Image.new('RGB', (400, 300), color=(240, 240, 245))
    draw = ImageDraw.Draw(img)
    
    # Create gradient effect
    for y in range(300):
        r = int(240 - (y * 0.3))
        g = int(240 - (y * 0.2))
        b = int(245 - (y * 0.1))
        draw.line([(0, y), (400, y)], fill=(r, g, b))
    
    # Add hotel icon (simple building shape)
    draw.rectangle([150, 80, 250, 180], outline=(100, 100, 100), width=3)
    draw.rectangle([160, 90, 190, 120], outline=(150, 150, 150), width=2)
    draw.rectangle([210, 90, 240, 120], outline=(150, 150, 150), width=2)
    draw.rectangle([160, 130, 190, 160], outline=(150, 150, 150), width=2)
    draw.rectangle([210, 130, 240, 160], outline=(150, 150, 150), width=2)
    
    # Add text
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    # Hotel name
    text = hotel_name.replace('_', ' ').replace('.jpg', '').title()
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    draw.text(((400 - text_width) // 2, 200), text, fill=(60, 60, 60), font=font)
    
    # Save image
    img.save(filename, 'JPEG', quality=85)
    print(f"Created {filename}")

# Create images directory if it doesn't exist
os.makedirs('assets/images', exist_ok=True)

# Generate all hotel images
for image_name in hotel_images:
    hotel_name = image_name.replace('.jpg', '').replace('_', ' ')
    create_hotel_placeholder(f'assets/images/{image_name}', hotel_name)

print(f"\n✅ Created {len(hotel_images)} hotel placeholder images!")
print("Images are located in: assets/images/")
