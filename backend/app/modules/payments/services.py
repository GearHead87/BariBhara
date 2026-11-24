from datetime import UTC, datetime
from typing import Any

from app.core.exceptions import ConflictError, NotFoundError
from app.core.pagination import Page
from app.modules.leases.repositories import LeaseRepository
from app.modules.payments.models import PaymentStatus, RentPayment
from app.modules.payments.repositories import PaymentFilters, PaymentRepository
from app.modules.payments.schemas import PaymentCreate, PaymentUpdate
from app.modules.users.models import RoleName, User


def compute_status(amount_due: int, amount_paid: int) -> PaymentStatus:
    if amount_paid <= 0:
        return PaymentStatus.DUE
    if amount_paid < amount_due:
        return PaymentStatus.PARTIAL
    return PaymentStatus.PAID


class PaymentService:
    def __init__(self, payments: PaymentRepository, leases: LeaseRepository) -> None:
        self.payments = payments
        self.leases = leases

    async def list(self, user: User, filters: PaymentFilters, page: Page) -> list[RentPayment]:
        if user.role_name == RoleName.TENANT:
            filters = PaymentFilters(
                month=filters.month,
                status=filters.status,
                lease_id=filters.lease_id,
                tenant_id=user.id,
            )
        return await self.payments.search(filters, page)

    async def get(self, user: User, payment_id: int) -> RentPayment:
        payment = await self.payments.get(payment_id)
        if payment is None or (
            user.role_name == RoleName.TENANT and payment.lease.tenant_id != user.id
        ):
            raise NotFoundError("Payment record not found")
        return payment

    async def create(self, data: PaymentCreate) -> RentPayment:
        lease = await self.leases.get(data.lease_id)
        if lease is None:
            raise NotFoundError("Lease not found")
        if await self.payments.exists_for_month(lease.id, data.month):
            raise ConflictError(
                f"A rent record for {data.month} already exists for {lease.tenant.full_name}"
            )

        values = data.model_dump()
        values["amount_due"] = data.amount_due or lease.monthly_rent
        self._apply_rules(values)
        payment = RentPayment(**values)
        await self.payments.add(payment)
        await self.payments.commit()
        return await self._fresh(payment.id)

    async def update(self, payment_id: int, data: PaymentUpdate) -> RentPayment:
        payment = await self._get_admin(payment_id)
        changes = data.changes()
        if "month" in changes and await self.payments.exists_for_month(
            payment.lease_id, changes["month"], exclude_id=payment.id
        ):
            raise ConflictError(f"A rent record for {changes['month']} already exists")

        merged = {
            "amount_due": payment.amount_due,
            "amount_paid": payment.amount_paid,
            "paid_at": payment.paid_at,
            **changes,
        }
        self._apply_rules(merged)
        changes["status"] = merged["status"]
        changes["paid_at"] = merged["paid_at"]
        await self.payments.update(payment, changes)
        await self.payments.commit()
        return await self._fresh(payment.id)

    async def delete(self, payment_id: int) -> None:
        payment = await self._get_admin(payment_id)
        await self.payments.delete(payment)
        await self.payments.commit()

    @staticmethod
    def _apply_rules(values: dict[str, Any]) -> None:
        """status is always derived from the amounts; a payment gets a paid_at timestamp."""
        values["status"] = compute_status(values["amount_due"], values["amount_paid"])
        if values["amount_paid"] > 0 and values.get("paid_at") is None:
            values["paid_at"] = datetime.now(UTC)
        if values["amount_paid"] == 0:
            values["paid_at"] = None

    async def _get_admin(self, payment_id: int) -> RentPayment:
        payment = await self.payments.get(payment_id)
        if payment is None:
            raise NotFoundError("Payment record not found")
        return payment

    async def _fresh(self, payment_id: int) -> RentPayment:
        payment = await self.payments.get(payment_id, refresh=True)
        if payment is None:
            raise NotFoundError("Payment record not found")
        return payment
