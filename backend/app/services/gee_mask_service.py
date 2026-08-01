from app.services import gee_service as gee_service_module

ee = gee_service_module.ee


class GeeMaskService:
    def build_binary_mask(self, asset_id: str, validated_band_name: str, asset_type: str = "IMAGE"):
        """Build a binary self-masked mangrove mask from a validated band.

        Args:
            asset_id: Earth Engine asset ID.
            validated_band_name: The band to select and threshold.
            asset_type: "IMAGE" (default) or "IMAGE_COLLECTION". When the asset is an
                ImageCollection it is mosaiced before band selection; this is required for
                the public global GMW 2020 collection.
        """
        if asset_type == "IMAGE_COLLECTION":
            return (
                ee.ImageCollection(asset_id)
                .mosaic()
                .select([validated_band_name])
                .gt(0)
                .selfMask()
            )
        return ee.Image(asset_id).select([validated_band_name]).gt(0).selfMask()

    def select_validated_mask_band(self, band_names: list) -> str:
        if not band_names:
            raise ValueError("No mask bands are available for binary mask construction.")
        return band_names[0]


gee_mask_service = GeeMaskService()
