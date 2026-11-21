from datetime import date

from conftest import MINH_HOA
from app.models import CitationIn
from app.store import graph, load, norms, phien_ban_tai, search, tim_dieu_khoan, verify

C = load(MINH_HOA)
DK = tim_dieu_khoan(C, "02/2026/TT-MINHHOA", "2", "1")


def test_load_sample():
    assert len(C.van_ban) == 3
    assert all(v.minh_hoa for v in C.van_ban)
    assert all("MINHHOA" in v.so_hieu for v in C.van_ban)


def test_bien_trai_tinh():
    assert phien_ban_tai(DK, date(2026, 3, 1)).nguon_sua_doi is None


def test_bien_phai_khong():
    assert phien_ban_tai(DK, date(2026, 7, 1)).nguon_sua_doi.so_hieu == "03/2026/TT-MINHHOA"


def test_ngay_truoc_cuoi():
    assert phien_ban_tai(DK, date(2026, 6, 30)).nguon_sua_doi is None


def test_truoc_hieu_luc():
    assert phien_ban_tai(DK, date(2026, 1, 1)) is None


def test_search_casefold():
    hits = search(C, "Bê Tông", date(2026, 8, 1), 5)
    assert hits and hits[0].so_hieu == "02/2026/TT-MINHHOA" and hits[0].dieu == "1"


def test_search_as_of_loc_phien_ban():
    texts = [h.noi_dung for h in search(C, "Điều 2 Khoản 1", date(2026, 8, 1), 50)]
    assert texts and not any("gốc" in t for t in texts)


def test_verify_valid_truoc_sua_doi():
    r = verify(C, CitationIn(so_hieu="02/2026/TT-MINHHOA", dieu="2", khoan="1", quote="gốc"), date(2026, 4, 1))
    assert r.status == "valid" and r.amended_by == [] and r.quote_match == 1.0


def test_verify_not_found():
    r = verify(C, CitationIn(so_hieu="X", dieu="1", khoan="1"), date(2026, 8, 1))
    assert r.status == "not_found" and r.exists is False


def test_verify_not_in_force():
    r = verify(C, CitationIn(so_hieu="02/2026/TT-MINHHOA", dieu="2", khoan="1"), date(2026, 1, 1))
    assert r.status == "not_in_force" and r.exists is True and r.current_text is None


def test_verify_quote_lech():
    r = verify(C, CitationIn(so_hieu="02/2026/TT-MINHHOA", dieu="2", khoan="1", quote="hoàn toàn khác"), date(2026, 8, 1))
    assert 0.0 <= r.quote_match < 1.0


def test_graph_bo_de_xuat():
    g = graph(C, "03/2026/TT-MINHHOA", 1)
    assert {e.dich for e in g.edges} == {"02/2026/TT-MINHHOA"}


def test_graph_depth2():
    g = graph(C, "03/2026/TT-MINHHOA", 2)
    assert {n.so_hieu for n in g.nodes} == {"01/2026/ND-MINHHOA", "02/2026/TT-MINHHOA", "03/2026/TT-MINHHOA"}
    assert len(g.edges) == 2


def test_graph_khong_co():
    assert graph(C, "X", 1) is None


def test_norms_ma_hieu():
    assert [d.ma_hieu for d in norms(C, "mh.0001", None)] == ["MH.0001"]


def test_norms_keyword():
    assert [d.ma_hieu for d in norms(C, None, "BÊ TÔNG")] == ["MH.0001"]


def test_search_nfd():
    import unicodedata
    assert search(C, unicodedata.normalize("NFD", "bê tông"), date(2026, 8, 1), 5)
    assert norms(C, None, unicodedata.normalize("NFD", "bê tông"))


def test_graph_canh_giua_node_cuoi():
    from app.models import Corpus, QuanHe, VanBan
    vb = lambda s: VanBan(so_hieu=s, loai="x", co_quan_ban_hanh="x", ngay_ban_hanh=date(2026, 1, 1),
                          ngay_hieu_luc=date(2026, 1, 1), tinh_trang="con_hieu_luc")
    qh = lambda a, b: QuanHe(nguon=a, dich=b, loai="can_cu", trang_thai_duyet="da_duyet")
    c = Corpus(van_ban=[vb("A"), vb("B"), vb("C")], dieu_khoan=[], dinh_muc=[],
               quan_he=[qh("B", "A"), qh("C", "A"), qh("B", "C")])
    assert len(graph(c, "A", 1).edges) == 3
