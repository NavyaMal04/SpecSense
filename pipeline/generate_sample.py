import os

def create_sample_pdf():
    os.makedirs("data/samples", exist_ok=True)
    pdf_path = "data/samples/sample_spec.pdf"

    pdf_bytes = (
        b'%PDF-1.4\n'
        b'1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n'
        b'2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n'
        b'3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n'
        b'4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n'
        b'5 0 obj << /Length 310 >> stream\n'
        b'BT\n'
        b'/F1 12 Tf\n'
        b'50 750 Td (ACME Industrial Motor - Model X100) Tj\n'
        b'0 -20 Td (Category: Electric Motors) Tj\n'
        b'0 -20 Td (Dimensions: 12 x 8 x 8 inches) Tj\n'
        b'0 -20 Td (Material: Cast Iron & Stainless Steel) Tj\n'
        b'0 -20 Td (Voltage: 230V AC / 60Hz 3-Phase) Tj\n'
        b'0 -20 Td (Certifications: UL Listed, CE Certified) Tj\n'
        b'0 -20 Td (Weight: 45.5 lbs) Tj\n'
        b'0 -20 Td (Price: $599.99) Tj\n'
        b'ET\n'
        b'endstream\n'
        b'endobj\n'
        b'xref\n'
        b'0 6\n'
        b'0000000000 65535 f \n'
        b'0000000009 00000 n \n'
        b'0000000058 00000 n \n'
        b'0000000115 00000 n \n'
        b'0000000236 00000 n \n'
        b'0000000305 00000 n \n'
        b'trailer << /Size 6 /Root 1 0 R >>\n'
        b'startxref\n'
        b'670\n'
        b'%%EOF\n'
    )

    with open(pdf_path, 'wb') as f:
        f.write(pdf_bytes)
    print(f"Sample PDF created at '{pdf_path}'")

if __name__ == "__main__":
    create_sample_pdf()
