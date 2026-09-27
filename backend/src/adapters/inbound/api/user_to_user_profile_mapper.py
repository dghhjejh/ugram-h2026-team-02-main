from src.application.dtos import PrivateUserProfileResponse, PublicUserProfileResponse
from src.domain.users.entities import User


class UserToUserProfileMapper:
    @staticmethod
    def to_public_user_profile_response(user: User) -> PublicUserProfileResponse:
        return PublicUserProfileResponse(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            profile_photo_url=user.profile_photo_url,
            registration_date=user.registration_date,
        )

    @staticmethod
    def to_private_user_profile_response(user: User) -> PrivateUserProfileResponse:
        return PrivateUserProfileResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            phone_number=user.phone_number,
            profile_photo_url=user.profile_photo_url,
            registration_date=user.registration_date,
        )
