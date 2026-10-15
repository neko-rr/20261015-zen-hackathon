"""ファイル内の著作権表示。通信しない。"""

import io

from PIL import Image

from app.file_facts import read_file_facts


def _jpeg() -> bytes:
    buffer = io.BytesIO()
    image = Image.new("RGB", (8, 8), "white")
    exif = Image.Exif()
    exif[315] = "Ada Lovelace"
    exif[33432] = "Copyright Ada"
    sub = exif.get_ifd(0x8769)
    sub[0xA420] = "CAM-1"
    image.save(buffer, format="JPEG", exif=exif)
    return buffer.getvalue()


def _insert_after_soi(jpeg: bytes, segment: bytes) -> bytes:
    assert jpeg.startswith(b"\xff\xd8")
    return jpeg[:2] + segment + jpeg[2:]


def test_exif_artist_and_copyright() -> None:
    facts = read_file_facts(_jpeg())
    assert facts["artist"] == "Ada Lovelace"
    assert facts["copyright"] == "Copyright Ada"
    assert facts["image_id"] == "CAM-1"
    assert facts["c2pa"] == "absent"


def test_xmp_url_credit_and_stock_id_override_camera_id() -> None:
    xml = (
        '<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:Description xmlns:dc="http://purl.org/dc/elements/1.1/"'
        ' xmlns:xmpRights="http://ns.adobe.com/xap/1.0/rights/"'
        ' xmlns:plus="http://ns.useplus.org/ldf/xmp/1.0/"'
        ' xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/"'
        ' dc:rights="Rights from xmp"'
        ' xmpRights:WebStatement="https://example.com/rights"'
        ' plus:ImageSupplierImageID="STOCK-42"'
        ' photoshop:Credit="Sample Agency">'
        "<dc:creator><rdf:Seq><rdf:li>XMP Artist</rdf:li></rdf:Seq></dc:creator>"
        "</rdf:Description></rdf:RDF></x:xmpmeta>"
    )
    packet = b"http://ns.adobe.com/xap/1.0/\x00" + xml.encode()
    segment = b"\xff\xe1" + (len(packet) + 2).to_bytes(2, "big") + packet
    facts = read_file_facts(_insert_after_soi(_jpeg(), segment))
    assert facts["artist"] == "Ada Lovelace"
    assert facts["copyright_url"] == "https://example.com/rights"
    assert facts["image_id"] == "STOCK-42"
    assert facts["credit"] == "Sample Agency"


def test_iptc_credit_and_comment() -> None:
    credit = "Visible credit".encode()
    dataset = bytes([0x1C, 0x02, 110]) + len(credit).to_bytes(2, "big") + credit
    resource = b"8BIM" + (0x0404).to_bytes(2, "big") + b"\x00\x00" + len(dataset).to_bytes(4, "big") + dataset
    header = b"Photoshop 3.0\x00" + resource
    app13 = b"\xff\xed" + (len(header) + 2).to_bytes(2, "big") + header
    comment = "Corner mark".encode()
    com = b"\xff\xfe" + (len(comment) + 2).to_bytes(2, "big") + comment
    facts = read_file_facts(_insert_after_soi(_jpeg(), app13 + com))
    assert facts["credit"] == "Visible credit"


def test_c2pa_generator_without_calling_it_verified() -> None:
    claim = b'{"claim_generator":"TestCam 1.0","urn:c2pa":"c2pa.claim"}'
    payload = b"JP\x00c2pa" + claim
    segment = b"\xff\xeb" + (len(payload) + 2).to_bytes(2, "big") + payload
    facts = read_file_facts(_insert_after_soi(_jpeg(), segment))
    assert facts["c2pa"] == "present"
    assert facts["c2pa_generator"] == "TestCam 1.0"


def test_plain_bytes_stay_unknown() -> None:
    facts = read_file_facts(b"not-an-image")
    assert facts["artist"] == "unknown"
    assert facts["copyright"] == "unknown"
    assert facts["c2pa"] == "absent"


def test_empty_image() -> None:
    assert read_file_facts(b"")["image_id"] == "unknown"
