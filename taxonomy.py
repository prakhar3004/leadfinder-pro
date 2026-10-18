"""
Global taxonomy of business niches, industries, manufacturing sectors, and global locations.
Supports small local stores, large industrial manufacturers, services, and B2B wholesale.
"""

INDUSTRY_TAXONOMY = {
    "🏭 Heavy Manufacturing & Factories": [
        "Textile & Garment Manufacturers",
        "Plastic & Injection Molding Manufacturers",
        "Metal Fabrication & CNC Machining",
        "Chemical & Dye Manufacturers",
        "Packaging, Corrugated Box & Carton Manufacturers",
        "Automobile Parts & Ancillary Manufacturers",
        "Food Processing Plants & FMCG Factories",
        "Electrical Panel & Transformer Manufacturers",
        "Leather Goods & Shoe Manufacturers",
        "Solar Panel & Renewable Equipment Manufacturers",
        "Foundry, Forging & Casting Works",
        "Steel, Pipe & Tube Manufacturers",
        "Pharmaceutical & API Manufacturers",
        "Plywood, Laminates & Timber Mills",
        "Glass & Ceramic Manufacturers",
        "Pumps, Valves & Industrial Machinery",
        "Paper & Pulp Mills",
        "Paints, Coatings & Adhesive Factories"
    ],
    "🏪 Small Local Stores & Retail": [
        "Kirana & General Provision Stores",
        "Hardware, Tools & Sanitary Ware",
        "Mobile Phone & Electronics Retailers",
        "Clothing, Saree & Boutique Stores",
        "Jewelry & Goldsmiths",
        "Stationery, Bookstores & Printing",
        "Sweet Shops, Bakeries & Confectionery",
        "Medical Stores & Chemists",
        "Furniture, Mattress & Home Decor",
        "Footwear & Shoe Stores",
        "Optical, Eyewear & Spectacles",
        "Auto Parts & Tyre Retailers",
        "Bicycle & Motorcycle Dealerships",
        "Gift, Toy & Novelty Shops",
        "Pooja Samagri & Religious Items",
        "Paint & Hardware Stores"
    ],
    "💼 B2B Wholesale & Distributors": [
        "FMCG Wholesale Distributors",
        "Building Material & Cement Dealers",
        "Textile & Fabric Wholesalers",
        "Grain, Spice & Pulses Merchants",
        "Electronic & Electrical Wholesalers",
        "Industrial Hardware & Fasteners Stockists",
        "Scrap, Metal & Recycling Traders",
        "Chemical & Solvent Traders",
        "Raw Plastic Granules Distributors",
        "Cosmetic & Personal Care Wholesalers"
    ],
    "🩺 Healthcare, Clinics & Medical": [
        "Dental Clinics & Hospitals",
        "Diagnostic & Pathology Labs",
        "Ayurvedic & Panchakarma Centers",
        "Homeopathic Clinics",
        "Physiotherapy & Rehabilitation",
        "Eye Clinics & Lasik Centers",
        "Skin & Cosmetic Dermatology Clinics",
        "Veterinary & Pet Clinics",
        "Orthopedic & Joint Clinics",
        "Polyclinics & Family Doctors"
    ],
    "🛠️ Contractors, Home & Local Services": [
        "Plumbers & Pipe Fitting",
        "Electricians & Wiring Contractors",
        "AC Repair, HVAC & Refrigeration",
        "Carpenters & Modular Kitchen Makers",
        "Architects & Interior Designers",
        "Civil Contractors & Building Construction",
        "Pest Control Services",
        "House Painting & Waterproofing",
        "CCTV, Security & Alarm Systems",
        "Solar Rooftop Installers",
        "Car Repair, Garage & Denting-Painting",
        "Dry Cleaners & Laundry Services"
    ],
    "🍽️ Hospitality, Food & Events": [
        "Restaurants & Fine Dining",
        "Cafes & Coffee Lounges",
        "Banquet Halls & Marriage Gardens",
        "Catering Services",
        "Cloud Kitchens & Tiffin Services",
        "Hotels, Resorts & Guest Houses",
        "Event Planners & Stage Decorators",
        "Bakeries & Custom Cake Shops"
    ],
    "💻 IT, Digital & Professional Services": [
        "Chartered Accountants & Tax Consultants",
        "Lawyers & Legal Advocates",
        "Digital Marketing & SEO Agencies",
        "Software & Web Development Companies",
        "Real Estate Agents & Property Dealers",
        "Graphic Design & Branding Studios",
        "Financial Planners & Loan Agents",
        "Insurance Brokers",
        "HR & Placement Agencies"
    ],
    "🏋️ Fitness, Beauty & Lifestyle": [
        "Gyms & Fitness Centers",
        "Beauty Salons & Parlors",
        "Spas & Massage Centers",
        "Yoga & Meditation Centers",
        "Dance, Music & Martial Arts Academies",
        "Tattoo & Piercing Studios"
    ],
    "🚚 Logistics, Warehouse & Freight": [
        "Packers & Movers",
        "Goods Transport & Fleet Operators",
        "Cold Storage Warehouses",
        "Courier & Cargo Companies",
        "Custom House Agents & Clearing Forwarding"
    ]
}

POPULAR_LOCATIONS = {
    "🇮🇳 India - Top Metro Cities": [
        "Delhi NCR",
        "Mumbai, Maharashtra",
        "Bengaluru, Karnataka",
        "Hyderabad, Telangana",
        "Pune, Maharashtra",
        "Ahmedabad, Gujarat",
        "Kolkata, West Bengal",
        "Chennai, Tamil Nadu"
    ],
    "📍 India - Targeted PIN Codes & Hubs": [
        "Mumbai - 400001 (Fort / South Mumbai)",
        "Mumbai - 400050 (Bandra West)",
        "Mumbai - 400069 (Andheri East MIDC)",
        "Delhi - 110001 (Connaught Place)",
        "Delhi - 110020 (Okhla Industrial Area)",
        "Bengaluru - 560001 (CBD / MG Road)",
        "Bengaluru - 560058 (Peenya Industrial Estate)",
        "Noida - 201301 (Sector 62/63 Commercial)",
        "Gurugram - 122016 (Cyber City / Udyog Vihar)",
        "Surat - 395002 (Textile & Diamond Market)",
        "Kanpur - 208001 (Leather & Trading Hub)",
        "Jaipur - 302001 (Johari Bazar & Gems)",
        "Ludhiana - 141003 (Industrial Area Hosiery)",
        "Ahmedabad - 380001 (Cloth Market & Trade)",
        "Pune - 411026 (Bhosari / Pimpri MIDC)"
    ],
    "🏭 India - Industrial & Commercial Hubs": [
        "Surat, Gujarat",
        "Kanpur, Uttar Pradesh",
        "Jaipur, Rajasthan",
        "Lucknow, Uttar Pradesh",
        "Ludhiana, Punjab",
        "Indore, Madhya Pradesh",
        "Vadodara, Gujarat",
        "Rajkot, Gujarat",
        "Coimbatore, Tamil Nadu",
        "Faridabad, Haryana",
        "Agra, Uttar Pradesh",
        "Nagpur, Maharashtra",
        "Ghaziabad, Uttar Pradesh",
        "Chandigarh Tri-City",
        "Vapi & Ankleshwar, Gujarat"
    ],
    "🇦🇪 UAE & Gulf Hubs": [
        "Dubai, UAE",
        "Abu Dhabi, UAE",
        "Sharjah, UAE",
        "Riyadh, Saudi Arabia",
        "Doha, Qatar"
    ],
    "🇺🇸 United States - Major Markets": [
        "New York, NY",
        "Los Angeles, CA",
        "Chicago, IL",
        "Houston, TX",
        "Dallas, TX",
        "Miami, FL",
        "Atlanta, GA",
        "San Francisco, CA"
    ],
    "🇬🇧 United Kingdom": [
        "London",
        "Birmingham",
        "Manchester",
        "Leeds",
        "Glasgow"
    ]
}
