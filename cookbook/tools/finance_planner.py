"""
title: Finance Planner
author: AI Lab
version: 1.0.0
description: Deterministic retirement and debt-payoff scenario comparisons.
"""

import json
import math


class Tools:
    @staticmethod
    def _bounded(name: str, value: float, minimum: float, maximum: float) -> float:
        numeric = float(value)
        if not math.isfinite(numeric) or not minimum <= numeric <= maximum:
            raise ValueError(f"{name} must be between {minimum} and {maximum}")
        return numeric

    def retirement_scenarios(
        self,
        current_savings: float,
        monthly_contribution: float,
        years: float,
        annual_return_percents: list[float],
        annual_fee_percent: float = 0.25,
        annual_inflation_percent: float = 2.0,
        withdrawal_rate_percent: float = 3.5,
    ) -> str:
        """Compare multiple constant-return retirement accumulation scenarios.

        :param current_savings: Starting retirement savings from 0 to 1 billion.
        :param monthly_contribution: End-of-month contribution from 0 to 10 million.
        :param years: Accumulation horizon from 1 month to 100 years.
        :param annual_return_percents: Two to five annual nominal return assumptions.
        :param annual_fee_percent: Annual fee deducted from each assumed return, from 0 to 20.
        :param annual_inflation_percent: Annual inflation assumption from -5 to 30.
        :param withdrawal_rate_percent: Illustrative first-year withdrawal rate from 0 to 20.
        """
        starting = self._bounded("current_savings", current_savings, 0, 1_000_000_000)
        contribution = self._bounded("monthly_contribution", monthly_contribution, 0, 10_000_000)
        horizon = self._bounded("years", years, 1 / 12, 100)
        fee = self._bounded("annual_fee_percent", annual_fee_percent, 0, 20)
        inflation = self._bounded("annual_inflation_percent", annual_inflation_percent, -5, 30)
        withdrawal = self._bounded("withdrawal_rate_percent", withdrawal_rate_percent, 0, 20)
        if not 2 <= len(annual_return_percents) <= 5:
            raise ValueError("annual_return_percents must contain two to five scenarios")
        returns = [
            self._bounded("annual_return_percent", value, -50, 100)
            for value in annual_return_percents
        ]
        months = round(horizon * 12)
        contributed = starting + contribution * months
        scenarios = []
        for assumed_return in returns:
            net_return = assumed_return - fee
            monthly_rate = (1 + net_return / 100) ** (1 / 12) - 1
            future_start = starting * (1 + monthly_rate) ** months
            future_contributions = (
                contribution * ((1 + monthly_rate) ** months - 1) / monthly_rate
                if monthly_rate
                else contribution * months
            )
            nominal = future_start + future_contributions
            real = nominal / (1 + inflation / 100) ** horizon
            annual_income = nominal * withdrawal / 100
            scenarios.append(
                {
                    "assumed_annual_return_percent": assumed_return,
                    "net_return_after_fee_percent": round(net_return, 4),
                    "ending_balance_nominal": round(nominal, 2),
                    "ending_balance_in_today_dollars": round(real, 2),
                    "total_contributed": round(contributed, 2),
                    "estimated_growth": round(nominal - contributed, 2),
                    "illustrative_first_year_withdrawal": round(annual_income, 2),
                    "illustrative_monthly_withdrawal": round(annual_income / 12, 2),
                }
            )
        return json.dumps(
            {
                "months": months,
                "annual_fee_percent": fee,
                "annual_inflation_percent": inflation,
                "withdrawal_rate_percent": withdrawal,
                "scenarios": scenarios,
                "assumptions": (
                    "Constant monthly-equivalent returns; end-of-month contributions; no taxes, "
                    "contribution-limit rules, sequence risk, or changes in contributions."
                ),
                "warning": (
                    "Educational scenarios only. Returns and sustainable withdrawals "
                    "are uncertain; "
                    "include adverse cases and verify tax and pension rules."
                ),
            },
            indent=2,
        )

    @staticmethod
    def _amortize(principal: float, monthly_rate: float, payment: float) -> dict:
        balance = principal
        total_interest = 0.0
        months = 0
        while balance > 0.005 and months < 1200:
            interest = balance * monthly_rate
            principal_payment = payment - interest
            if principal_payment <= 0:
                raise ValueError("monthly payment does not cover the first month's interest")
            total_interest += interest
            balance -= min(balance, principal_payment)
            months += 1
        if balance > 0.005:
            raise ValueError("repayment exceeds the 100-year calculation limit")
        return {"months": months, "total_interest": total_interest}

    def compare_debt_payoff(
        self,
        principal: float,
        annual_interest_percent: float,
        regular_monthly_payment: float,
        extra_monthly_payment: float,
    ) -> str:
        """Compare a regular debt payment with an additional monthly payment.

        :param principal: Current balance from 0.01 to 1 billion.
        :param annual_interest_percent: Nominal annual rate from 0 to 100 percent.
        :param regular_monthly_payment: Existing monthly payment from 0.01 to 100 million.
        :param extra_monthly_payment: Additional monthly payment from 0 to 100 million.
        """
        balance = self._bounded("principal", principal, 0.01, 1_000_000_000)
        rate = self._bounded("annual_interest_percent", annual_interest_percent, 0, 100)
        regular = self._bounded(
            "regular_monthly_payment", regular_monthly_payment, 0.01, 100_000_000
        )
        extra = self._bounded("extra_monthly_payment", extra_monthly_payment, 0, 100_000_000)
        monthly_rate = rate / 100 / 12
        baseline = self._amortize(balance, monthly_rate, regular)
        accelerated = self._amortize(balance, monthly_rate, regular + extra)
        return json.dumps(
            {
                "baseline": {
                    "monthly_payment": round(regular, 2),
                    "months": baseline["months"],
                    "total_interest": round(baseline["total_interest"], 2),
                },
                "accelerated": {
                    "monthly_payment": round(regular + extra, 2),
                    "months": accelerated["months"],
                    "total_interest": round(accelerated["total_interest"], 2),
                },
                "months_saved": baseline["months"] - accelerated["months"],
                "interest_saved": round(
                    baseline["total_interest"] - accelerated["total_interest"], 2
                ),
                "assumptions": (
                    "Fixed nominal rate compounded monthly; payments monthly; no fees, penalties, "
                    "rate changes, tax effects, or lender-specific daily interest."
                ),
                "warning": "Confirm prepayment terms and request a lender payoff statement.",
            },
            indent=2,
        )
