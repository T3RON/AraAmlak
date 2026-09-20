"""
factory_boy factories for the core models used in tests.
"""

import factory
from factory.django import DjangoModelFactory

from apps.accounts.models import CustomUser
from apps.agencies.models import Agency, AgencyMember, Branch
from apps.crm.models import Request as CrmRequest
from apps.listings.models import DealType, Listing, PropertyType


class AgencyFactory(DjangoModelFactory):
    class Meta:
        model = Agency

    name = factory.Sequence(lambda n: f"آژانس شماره {n}")
    slug = factory.Sequence(lambda n: f"agency-{n}")
    plan = "free"
    is_active = True


class CustomUserFactory(DjangoModelFactory):
    class Meta:
        model = CustomUser

    # Use fake phone numbers in tests — never real ones
    phone = factory.Sequence(lambda n: f"0900000{n:04d}")
    full_name = factory.Sequence(lambda n: f"کاربر تست {n}")
    agency = factory.SubFactory(AgencyFactory)
    role = "agent"
    is_active = True


class BranchFactory(DjangoModelFactory):
    class Meta:
        model = Branch

    agency = factory.SubFactory(AgencyFactory)
    name = factory.Sequence(lambda n: f"شعبه {n}")
    is_active = True


class AgencyMemberFactory(DjangoModelFactory):
    class Meta:
        model = AgencyMember

    user = factory.SubFactory(CustomUserFactory)
    agency = factory.SubFactory(AgencyFactory)
    role = "agent"


class ListingFactory(DjangoModelFactory):
    class Meta:
        model = Listing

    agency = factory.SubFactory(AgencyFactory)
    property_type = PropertyType.APARTMENT
    deal_type = DealType.SALE
    city = factory.Sequence(lambda n: f"شهر {n}")
    area = 80
    rooms = 2
    status = "active"


class RequestFactory(DjangoModelFactory):
    class Meta:
        model = CrmRequest

    agency = factory.SubFactory(AgencyFactory)
    client_name = factory.Sequence(lambda n: f"مراجعه‌کننده {n}")
    deal_type = DealType.SALE
    city = factory.Sequence(lambda n: f"شهر {n}")
    status = "new"
    priority = "normal"
