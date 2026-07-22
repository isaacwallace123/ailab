"""
title: Finance Calculator
author: AI Lab
version: 1.0.0
description: Educational compound-growth, loan, and inflation calculations.
"""

import json
import math


class Tools:
    @staticmethod
    def _bounded(name: str, value: float, minimum: float, maximum: float) -> float:
        if not math.isfinite(value) or not minimum <= value <= maximum:
            raise ValueError(f"{name} must be between {minimum} and {maximum}")
        return value

    def compound_growth(
        self,
        starting_amount: float,
        monthly_contribution: float,
        annual_return_percent: float,
        years: float,
        annual_fee_percent: float = 0.0,
    ) -> str:
        """Estimate compound growth with end-of-month contributions and a constant net return.

        :param starting_amount: Initial currency amount, from 0 to 1 billion.
        :param monthly_contribution: End-of-month contribution, from 0 to 10 million.
        :param annual_return_percent: Assumed annual nominal return, from -50 to 100 percent.
        :param years: Time horizon, from 0.08 to 100 years.
        :param annual_fee_percent: Annual fee deducted from return, from 0 to 20 percent.
        """
        principal = self._bounded("starting_amount", starting_amount, 0, 1_000_000_000)
        contribution = self._bounded("monthly_contribution", monthly_contribution, 0, 10_000_000)
        annual_return = self._bounded("annual_return_percent", annual_return_percent, -50, 100)
        fee = self._bounded("annual_fee_percent", annual_fee_percent, 0, 20)
        horizon = self._bounded("years", years, 1 / 12, 100)
        months = round(horizon * 12)
        monthly_rate = ((1 + (annual_return - fee) / 100) ** (1 / 12)) - 1
        future_start = principal * ((1 + monthly_rate) ** months)
        future_contributions = (
            contribution * (((1 + monthly_rate) ** months - 1) / monthly_rate)
            if monthly_rate
            else contribution * months
        )
        total_contributed = principal + contribution * months
        result = {
            "future_value": round(future_start + future_contributions, 2),
            "total_contributed": round(total_contributed, 2),
            "estimated_growth": round(future_start + future_contributions - total_contributed, 2),
            "months": months,
            "net_annual_return_percent": round(annual_return - fee, 4),
            "assumptions": (
                "Constant return and fee; end-of-month contributions; no tax or inflation."
            ),
            "warning": "Educational estimate only. Returns are uncertain and not guaranteed.",
        }
        return json.dumps(result, indent=2)

    def loan_payment(
        self,
        principal: float,
        annual_interest_percent: float,
        amortization_years: float,
        payments_per_year: int = 12,
    ) -> str:
        """Calculate a fixed-payment amortizing loan and total interest.

        :param principal: Amount borrowed, from 0.01 to 1 billion.
        :param annual_interest_percent: Nominal annual interest, from 0 to 100 percent.
        :param amortization_years: Repayment length, from 0.08 to 100 years.
        :param payments_per_year: Payment frequency from 1 to 52.
        """
        amount = self._bounded("principal", principal, 0.01, 1_000_000_000)
        rate = self._bounded("annual_interest_percent", annual_interest_percent, 0, 100)
        years = self._bounded("amortization_years", amortization_years, 1 / 12, 100)
        if not 1 <= payments_per_year <= 52:
            raise ValueError("payments_per_year must be between 1 and 52")
        periods = round(years * payments_per_year)
        periodic_rate = rate / 100 / payments_per_year
        payment = (
            amount * periodic_rate / (1 - (1 + periodic_rate) ** -periods)
            if periodic_rate
            else amount / periods
        )
        total_paid = payment * periods
        return json.dumps(
            {
                "payment": round(payment, 2),
                "number_of_payments": periods,
                "total_paid": round(total_paid, 2),
                "total_interest": round(total_paid - amount, 2),
                "assumptions": (
                    "Fixed nominal rate and equal payments; no fees, taxes, penalties, "
                    "or rate changes."
                ),
                "warning": (
                    "Educational estimate only; confirm lender compounding and contract terms."
                ),
            },
            indent=2,
        )

    def inflation_adjusted_value(
        self, future_amount: float, annual_inflation_percent: float, years: float
    ) -> str:
        """Convert a future nominal amount into today's purchasing power.

        :param future_amount: Future currency amount, from 0 to 1 trillion.
        :param annual_inflation_percent: Assumed annual inflation, from -10 to 50 percent.
        :param years: Time horizon, from 0 to 100 years.
        """
        amount = self._bounded("future_amount", future_amount, 0, 1_000_000_000_000)
        inflation = self._bounded("annual_inflation_percent", annual_inflation_percent, -10, 50)
        horizon = self._bounded("years", years, 0, 100)
        adjusted = amount / ((1 + inflation / 100) ** horizon)
        return json.dumps(
            {
                "future_nominal_amount": round(amount, 2),
                "today_purchasing_power": round(adjusted, 2),
                "annual_inflation_percent": inflation,
                "years": horizon,
                "warning": "Inflation varies; use multiple scenarios for planning.",
            },
            indent=2,
        )
