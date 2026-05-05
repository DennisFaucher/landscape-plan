from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, timezone


class Base(DeclarativeBase):
    pass


class Plant(Base):
    __tablename__ = "plants"

    id            = Column(Integer, primary_key=True, index=True)

    # ── User data ────────────────────────────────────────────────────────────
    image_path    = Column(String(500), default="")   # user-uploaded photo
    thumbnail_path = Column(String(500), default="")
    notes         = Column(Text, default="")           # personal notes

    # ── Trefle core / taxonomy ───────────────────────────────────────────────
    trefle_id          = Column(Integer)
    trefle_slug        = Column(String(200), default="")
    common_name        = Column(String(200), default="")
    scientific_name    = Column(String(200), default="")
    family             = Column(String(200), default="")
    family_common_name = Column(String(200), default="")
    genus              = Column(String(200), default="")
    year               = Column(Integer)
    author             = Column(String(200), default="")
    bibliography       = Column(String(500), default="")
    status             = Column(String(50),  default="")   # accepted | unknown
    rank               = Column(String(50),  default="")   # species | ssp | var | form | hybrid | subvar
    duration           = Column(String(200), default="[]") # JSON ["annual","perennial"]
    edible             = Column(Boolean)
    edible_part        = Column(String(200), default="[]") # JSON array
    vegetable          = Column(Boolean)
    observations       = Column(Text, default="")
    trefle_image_url   = Column(String(500), default="")
    synonyms           = Column(Text, default="[]")        # JSON [{name,author}]

    # ── Images (first URL per Trefle category) ───────────────────────────────
    image_flower = Column(String(500), default="")
    image_leaf   = Column(String(500), default="")
    image_habit  = Column(String(500), default="")
    image_fruit  = Column(String(500), default="")
    image_bark   = Column(String(500), default="")
    image_other  = Column(String(500), default="")

    # ── Distributions ────────────────────────────────────────────────────────
    distribution_native = Column(Text, default="[]")  # JSON [zone_name, ...]

    # ── Flower ───────────────────────────────────────────────────────────────
    flower_color       = Column(String(200), default="[]") # JSON array
    flower_conspicuous = Column(Boolean)

    # ── Foliage ──────────────────────────────────────────────────────────────
    foliage_texture = Column(String(50),  default="")      # fine | medium | coarse
    foliage_color   = Column(String(200), default="[]")    # JSON array
    leaf_retention  = Column(Boolean)

    # ── Fruit / Seed ─────────────────────────────────────────────────────────
    fruit_conspicuous = Column(Boolean)
    fruit_color       = Column(String(200), default="[]")  # JSON array
    fruit_shape       = Column(String(100), default="")
    seed_persistence  = Column(Boolean)

    # ── Specifications ───────────────────────────────────────────────────────
    ligneous_type       = Column(String(100), default="")  # liana|subshrub|shrub|tree|parasite
    growth_form         = Column(String(100), default="")
    growth_habit        = Column(String(200), default="")
    growth_rate         = Column(String(100), default="")
    average_height_cm   = Column(Integer)
    maximum_height_cm   = Column(Integer)
    nitrogen_fixation   = Column(String(100), default="")
    shape_and_orientation = Column(String(100), default="")
    toxicity            = Column(String(50),  default="")  # none|low|medium|high

    # ── Growth ───────────────────────────────────────────────────────────────
    description             = Column(Text,    default="")
    sowing                  = Column(Text,    default="")
    days_to_harvest         = Column(Integer)
    ph_minimum              = Column(Float)
    ph_maximum              = Column(Float)
    light                   = Column(Integer)   # 0-10
    atmospheric_humidity    = Column(Integer)   # 0-10
    growth_months           = Column(String(200), default="[]")  # JSON
    bloom_months            = Column(String(200), default="[]")  # JSON
    fruit_months            = Column(String(200), default="[]")  # JSON
    row_spacing_cm          = Column(Integer)
    spread_cm               = Column(Integer)
    minimum_precipitation_mm = Column(Integer)
    maximum_precipitation_mm = Column(Integer)
    minimum_root_depth_cm   = Column(Integer)
    minimum_temperature_deg_c = Column(Float)
    maximum_temperature_deg_c = Column(Float)
    soil_nutriments         = Column(Integer)   # 0-10
    soil_salinity           = Column(Integer)   # 0-10
    soil_texture            = Column(Integer)   # 0-10
    soil_humidity           = Column(Integer)   # 0-10

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
