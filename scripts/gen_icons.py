"""Gera os ícones PNG do PWA (sem dependências externas).

Uso: python scripts/gen_icons.py

Desenha um "M" branco sobre fundo verde. Os ícones "maskable" deixam margem
de segurança (o Android recorta em círculo/squircle); o apple-touch-icon é
quadrado cheio porque o iOS arredonda os cantos sozinho.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

DESTINO = Path(__file__).resolve().parent.parent / "moneyflow" / "assets" / "icons"
VERDE = (0, 131, 0)
BRANCO = (255, 255, 255)


def _dist_segmento(px: float, py: float, a: tuple, b: tuple) -> float:
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return ((px - (ax + t * dx)) ** 2 + (py - (ay + t * dy)) ** 2) ** 0.5


def _png(tamanho: int, margem: float) -> bytes:
    """`margem` é a fração do lado reservada em cada borda para o glifo."""
    m = tamanho * margem
    esq, dir_ = m, tamanho - m
    topo, base = m, tamanho - m
    meio = tamanho / 2
    pontos = [(esq, base), (esq, topo), (meio, base - (base - topo) * 0.45),
              (dir_, topo), (dir_, base)]
    segmentos = list(zip(pontos, pontos[1:], strict=False))
    espessura = tamanho * 0.055

    linhas = bytearray()
    for y in range(tamanho):
        linhas.append(0)  # filtro "nenhum"
        for x in range(tamanho):
            d = min(_dist_segmento(x + 0.5, y + 0.5, a, b) for a, b in segmentos)
            # 1px de suavização na borda do traço.
            cobertura = max(0.0, min(1.0, espessura - d + 0.5))
            cor = tuple(round(f * cobertura + v * (1 - cobertura))
                        for f, v in zip(BRANCO, VERDE, strict=True))
            linhas.extend(cor)

    def bloco(tipo: bytes, dados: bytes) -> bytes:
        corpo = tipo + dados
        return struct.pack(">I", len(dados)) + corpo + struct.pack(">I", zlib.crc32(corpo))

    cabecalho = struct.pack(">IIBBBBB", tamanho, tamanho, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", cabecalho)
            + bloco(b"IDAT", zlib.compress(bytes(linhas), 9)) + bloco(b"IEND", b""))


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    saidas = {
        "icon-192.png": (192, 0.27),
        "icon-512.png": (512, 0.27),
        "icon-maskable-512.png": (512, 0.33),  # zona segura de 80%
        "apple-touch-icon.png": (180, 0.27),
    }
    for nome, (tamanho, margem) in saidas.items():
        (DESTINO / nome).write_bytes(_png(tamanho, margem))
        print("gerado", DESTINO / nome)


if __name__ == "__main__":
    main()
