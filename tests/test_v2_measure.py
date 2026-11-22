import copy
import unittest

from scripts.v2_acceptance.measure import summarize


def stamp(seconds):
    return f"2026-01-01T00:00:{seconds:02}Z"


def sample(vehicle, event, field, seconds):
    return {"vehicleId": vehicle, "eventId": event, field: stamp(seconds)}


class MeasurementTest(unittest.TestCase):
    def setUp(self):
        self.first = {
            "id": "trial-1", "target": "vehicle-001", "status": "PASS",
            "windowStart": stamp(0), "windowEnd": stamp(9), "obstructionAt": stamp(0),
            "clearAt": stamp(2), "faultEventId": "fault", "firstHealthyEventId": "healthy",
            "recoveredEventId": "recovered",
            "source": [sample("vehicle-001", event, "sourceTimestamp", at)
                       for event, at in (("fault", 1), ("healthy", 3), ("recovered", 5))],
            "stages": {
                "companion": [sample("vehicle-001", "fault", "observedAt", at) for at in (2, 1, 2)],
                "twin": [sample("vehicle-002", "fault", "observedAt", 2), sample("vehicle-001", "fault", "observedAt", 3)],
                "api": [],
            },
            "resources": [
                {"sampledAt": stamp(1), "target": "test-backend", "cpuPercent": 5, "memoryBytes": 1000},
                {"sampledAt": stamp(2), "target": "test-backend", "cpuPercent": 9, "memoryBytes": 1200},
            ],
        }
        self.run = {"scope": "SYNTHETIC_CHECK", "implementationSha": "0" * 40,
                    "clockUncertaintyMs": 5, "trials": [self.first]}

    def test_counts_first_delivery_without_treating_duplicate_or_alien_id_as_new_update(self):
        result = summarize(self.run)["trials"][0]
        companion = result["stages"]["companion"]
        self.assertEqual(companion["byVehicle"]["vehicle-001"], {"matchingUnique": 1, "eligibleSourceUnique": 3})
        self.assertEqual({key: value for key, value in companion.items() if key != "byVehicle"}, {
            "matchingUnique": 1, "eligibleSourceUnique": 3, "duplicateDeliveries": 2, "unmatchedUnique": 0,
        })
        self.assertEqual(result["stages"]["twin"]["unmatchedUnique"], 1)
        self.assertEqual(result["stages"]["api"]["matchingUnique"], 0)
        self.assertEqual(result["stages"]["browser"], {"status": "NOT_CAPTURED"})
        self.assertEqual(result["timingsMilliseconds"]["sourceToCompanionMs"]["median"], 0)
        self.assertEqual(result["timingsMilliseconds"]["groundTruthToFaultSourceMs"]["median"], 1000)
        self.assertEqual(result["timingsMilliseconds"]["groundTruthClearToRecoveredSourceMs"]["median"], 3000)
        self.assertEqual(result["timingsMilliseconds"]["healthyWindowToRecoveredSourceMs"]["median"], 2000)
        self.assertEqual(result["resources"]["test-backend"]["memoryBytes"]["median"], 1100)
        self.assertIsNotNone(result["resources"]["test-backend"]["cpuPercent"]["sampleStdDev"])

    def test_timeout_is_retained_and_inconsistent_clock_sample_excluded(self):
        timeout = copy.deepcopy(self.first)
        timeout.update(id="trial-2", status="TIMED_OUT", reason="no browser observation")
        timeout["stages"]["twin"].append(sample("vehicle-001", "healthy", "observedAt", 0))
        self.run["trials"].append(timeout)
        result = summarize(self.run)
        self.assertEqual(result["trialOutcomes"]["TIMED_OUT"], 1)
        self.assertEqual(result["trialMedianDistributionsMilliseconds"]["groundTruthClearToRecoveredSourceMs"]["n"], 2)
        self.assertEqual(result["trials"][1]["clockConflicts"][0]["milliseconds"], -3000)
        self.assertEqual(result["trials"][1]["timingsMilliseconds"]["sourceToTwinMs"]["n"], 1)

    def test_changed_source_timestamp_for_retried_identity_fails(self):
        self.first["source"].append(sample("vehicle-001", "fault", "sourceTimestamp", 3))
        with self.assertRaisesRegex(ValueError, "changed source timestamp"):
            summarize(self.run)
