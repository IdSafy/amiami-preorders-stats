from dataclasses import dataclass, field
import datetime
import aiohttp
from pydantic import BaseModel, Field

class LatestFxRatesResponse(BaseModel):
    success: bool
    timestamp: int
    base: str
    date: datetime.date
    rates: dict[str, float]

@dataclass
class FxRatesService:
    access_key: str
    ttl_seconds: int = 60*60*24  # 1 day
    _cache: dict[str, LatestFxRatesResponse] = field(default_factory=dict, init=False)

    async def _get_rates_data(self) -> LatestFxRatesResponse:
        url = f'https://api.exchangeratesapi.io/v1/latest'
        async with aiohttp.ClientSession() as session:
            # base is EUR by default
            async with session.get(url, params={'access_key': self.access_key, "symbols": "USD,JPY"}) as response: 
                data = await response.json()
                return LatestFxRatesResponse.model_validate(data)

    async def _get_cached_rates(self) -> dict[str, float]:
        cached = self._cache.get('rates')
        if cached is not None:
            cache_time = datetime.datetime.fromtimestamp(cached.timestamp)
            if (datetime.datetime.now() - cache_time).total_seconds() < self.ttl_seconds:
                return cached.rates
        rates_data = await self._get_rates_data()
        self._cache['rates'] = rates_data
        return rates_data.rates

    async def get_jpy_to_usd_rate(self) -> float:
        rates = await self._get_cached_rates()
        return rates['USD'] / rates['JPY']
