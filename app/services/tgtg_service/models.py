from pydantic import BaseModel
from typing import Optional

class PriceInfo(BaseModel):
    code: str
    minor_units: int
    decimals: int

    def __str__(self) -> str:
        formatted_item_value = self.minor_units / (10 ** self.decimals)
        return f"{formatted_item_value:,.2f}{self.__code_symbol()}"

    def __code_symbol(self) -> str:
        if self.code == "EUR":
            return "€"
        elif self.code == "USD":
            return "$"
        else:
            return self.code

class Picture(BaseModel):
    picture_id: str
    current_url: str
    is_automatically_created: bool

class Address(BaseModel):
    address: dict
    @property
    def country(self) -> str:
        return self.address.get("country", "Unknown")

    @property
    def latitude(self) -> Optional[float]:
        return self.address.get("latitude")

class Store(BaseModel):
    store_id: str
    store_name: str
    website: Optional[str] = None
    store_location: Address
    logo_picture: Picture
    store_time_zone: str
    cover_picture: Picture

class Item(BaseModel):
    item_id: str
    item_price: PriceInfo
    item_value: PriceInfo
    cover_picture: Picture
    logo_picture: Picture
    name: str
    description: Optional[str] = None
    collection_info: Optional[str] = None

class PickupInterval(BaseModel):
    start: str
    end: str

class PickupLocation(BaseModel):
    address: dict
    location: dict

class ItemDetails(BaseModel):
    item: Item
    store: Store
    display_name: str
    purchase_end: Optional[str] = None
    items_available: int
    distance: float
    favorite: bool
    item_type: str
    sold_out_at: Optional[str] = None
    pickup_location: Optional[PickupLocation] = None
    pickup_interval: Optional[PickupInterval] = None