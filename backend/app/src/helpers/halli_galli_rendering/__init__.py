"""Detailed rendering stages used by :mod:`helpers.halli_galli_card`.

The central API owns all tuning constants and orchestrates generation.
``models`` holds immutable metadata; ``assets``, ``layout``, and ``svg`` prepare
fruit artwork. ``colors`` and ``masks`` supply shared operations. ``decoys`` and
``background`` balance colors; ``artifacts`` paints surface and card-wide marks.

Stages import constants from the central API. That API defers stage imports
until generation, allowing either import order without circular initialization.
All rendering is in memory; external scripts save previews and test artifacts.
"""
