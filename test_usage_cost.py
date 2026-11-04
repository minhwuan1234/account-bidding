import unittest

from business.usage_cost import summarize_usage


class UsageCostTests(unittest.TestCase):
    def test_luna_tokens_and_cached_tokens(self):
        result = summarize_usage({
            "model": "gpt-6-luna",
            "usage": {"input_tokens": 1000, "output_tokens": 200,
                      "input_tokens_details": {"cached_tokens": 100, "cache_write_tokens": 50}},
        })
        expected = (850 * 0.10 + 100 * 0.01 + 50 * 0.125 + 200 * 0.50) / 1_000_000
        self.assertAlmostEqual(result["estimated_cost_usd"], expected)

    def test_unknown_model_does_not_claim_zero_cost(self):
        result = summarize_usage({"model": "custom-model", "usage": {"input_tokens": 100, "output_tokens": 50}})
        self.assertIsNone(result["estimated_cost_usd"])

    def test_no_usage_is_unknown(self):
        self.assertIsNone(summarize_usage({"model": "gpt-6-luna"}))


if __name__ == "__main__":
    unittest.main()
