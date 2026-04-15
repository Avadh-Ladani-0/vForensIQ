# Complete Manual Evaluation Record — Sprint 4 (75 Questions)

Every question evaluated across B1, B2-Cypher, B2-Hybrid, B3-AQR.
Manual verdict: PASS if answer is factually correct from any valid operator perspective.
Date: 2026-04-15 | Model: gpt-4o | Scenario: ai_hw_summit_day1

---

## L1 (15 questions)

### L1_q002_car_entry_count_at_parkinglot
**Q:** How many car_entry events were recorded at Gate_ParkingLot on 2025-12-08 (UTC)?
**Gold (sql):** 381

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | There were 381 car_entry events recorded at Gate_ParkingLot on 2025-12-08 (UTC).... | PASS | PASS |  |
| b2_rag_cypher | There were 381 car_entry events recorded at Gate_ParkingLot on 2025-12-08 (UTC).... | PASS | PASS |  |
| b2_rag_hybrid | A total of 381 car entry events were recorded at Gate_ParkingLot on December 8, 2025 (UTC). This figure highlights the s... | PASS | PASS |  |
| b3_aqr | There were 381 car_entry events recorded at Gate_ParkingLot on 2025-12-08 (UTC).... | PASS | PASS |  |

### L1_q003_person_entry_at_keynote_door
**Q:** How many person_entry events were recorded at KeynoteHall_DoorA on 2025-12-08 (UTC)?
**Gold (sql):** 782

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | There were 782 person_entry events recorded at KeynoteHall_DoorA on 2025-12-08 (UTC).... | PASS | PASS |  |
| b2_rag_cypher | There were 782 person_entry events recorded at KeynoteHall_DoorA on 2025-12-08 (UTC).... | PASS | PASS |  |
| b2_rag_hybrid | On December 8, 2025, there were 782 person entry events recorded at KeynoteHall_DoorA. The observation period for CCTV a... | FAIL | FAIL |  |
| b3_aqr | There were 782 person_entry events recorded at KeynoteHall_DoorA on 2025-12-08.... | PASS | PASS |  |

### L1_q004_total_events_in_summit_day
**Q:** How many total events of any type were recorded across all cameras during the entire day of 2025-12-08 (UTC)?
**Gold (sql):** 437940

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | There were 437,940 total events recorded across all cameras on 2025-12-08 (UTC).... | PASS | PASS |  |
| b2_rag_cypher | A total of 437,940 events of any type were recorded across all cameras on 2025-12-08 (UTC).... | PASS | PASS |  |
| b2_rag_hybrid | A total of 437,940 events of various types were recorded across all cameras on December 8, 2025 (UTC). The day's surveil... | PASS | PASS |  |
| b3_aqr | There were 437,940 total events recorded across all cameras on 2025-12-08 (UTC).... | PASS | PASS |  |

### L1_q005_distinct_object_ids_at_main_entrance
**Q:** How many distinct object_id values were tracked at Gate_MainEntrance across all entry/exit events on 2025-12-08 (UTC)?
**Gold (sql):** 2951

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | There were 2,951 distinct object_id values tracked at Gate_MainEntrance across all entry/exit events on December 8, 2025... | PASS | PASS |  |
| b2_rag_cypher | There were 2,951 distinct object_id values tracked at Gate_MainEntrance across all entry/exit events on 2025-12-08 (UTC)... | PASS | PASS |  |
| b2_rag_hybrid | On December 8, 2025, a total of 2,951 distinct object_id values were tracked at Gate_MainEntrance across all entry and e... | FAIL | FAIL |  |
| b3_aqr | There were 2,951 distinct object_id values tracked at Gate_MainEntrance across all entry/exit events on 2025-12-08 (UTC)... | PASS | PASS |  |

### L1_q006_active_cameras_during_keynote
**Q:** How many distinct cameras produced at least one event between 09:00 and 10:00 UTC on 2025-12-08 (the morning keynote hour)?
**Gold (sql):** 8

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | Eight distinct cameras produced at least one event between 09:00 and 10:00 UTC on 2025-12-08.... | PASS | PASS |  |
| b2_rag_cypher | Eight distinct cameras produced at least one event between 09:00 and 10:00 UTC on 2025-12-08.... | PASS | PASS |  |
| b2_rag_hybrid | Eight distinct cameras produced at least one event between 09:00 and 10:00 UTC on December 8, 2025. During the surroundi... | PASS | PASS |  |
| b3_aqr | There were 8 distinct cameras that produced at least one event between 09:00 and 10:00 UTC on 2025-12-08.... | PASS | PASS |  |

### L1_q007_cars_into_parking_lot
**Q:** How many cars came into the parking lot during the day?
**Gold (sql):** 381

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | There were 381 cars that came into the parking lot during the day on December 8, 2025.... | PASS | PASS |  |
| b2_rag_cypher | There were 0 car_entry events into the parking lot on December 8, 2025.... | FAIL | FAIL |  |
| b2_rag_hybrid | No cars came into the parking lot during the day. This is supported by the precise count from structured data, indicatin... | FAIL | FAIL |  |
| b3_aqr | There were 381 car_entry events into the parking lot during the day on December 8, 2025.... | PASS | PASS |  |

### L1_q008_people_through_main_gate
**Q:** How many people in total went through the main entrance gate, counting both people arriving and people leaving?
**Gold (sql):** 2883

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | A total of 2,883 people went through the main entrance gate, including both arrivals and departures.... | PASS | PASS |  |
| b2_rag_cypher | A total of 2883 people went through the main entrance gate on December 8, 2025, counting both arrivals and departures.... | PASS | PASS |  |
| b2_rag_hybrid | A total of 2,883 people went through the main entrance gate, accounting for both arrivals and departures. This figure hi... | PASS | PASS |  |
| b3_aqr | There were 2,883 people who went through the main entrance gate, counting both arrivals and departures.... | PASS | PASS |  |

### L1_q009_total_cameras_at_venue
**Q:** How many cameras are deployed at this venue?
**Gold (sql):** 8

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | There are 8 cameras deployed at this venue.... | PASS | PASS |  |
| b2_rag_cypher | There are 8 cameras deployed at this venue.... | PASS | PASS |  |
| b2_rag_hybrid | There are 8 cameras deployed at this venue. These cameras cover diverse locations such as the DemoBooth, ExpoFloor, Food... | PASS | PASS |  |
| b3_aqr | There are 8 cameras deployed at this venue.... | PASS | PASS |  |

### L1_q010_person_exits_main_gate
**Q:** How many people left through the main entrance gate today?
**Gold (sql):** 1352

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | 1,352 people left through the main entrance gate today.... | PASS | PASS |  |
| b2_rag_cypher | 1,352 people exited through the main entrance gate today.... | PASS | PASS |  |
| b2_rag_hybrid | Today, 1,352 people exited through the main entrance gate. There was significant foot traffic recorded throughout variou... | PASS | PASS |  |
| b3_aqr | There were 1,352 people who exited through the main entrance gate today.... | PASS | PASS |  |

### L1_q011_car_exits_parking
**Q:** How many cars drove out of the parking lot?
**Gold (sql):** 397

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | There were 397 car_exit events from the parking lot on December 8, 2025.... | PASS | PASS |  |
| b2_rag_cypher | There were 0 car_exit events recorded for cars driving out of the parking lot on December 8, 2025.... | FAIL | FAIL |  |
| b2_rag_hybrid | No cars drove out of the parking lot according to the specific Cypher query results. However, across various camera loca... | FAIL | FAIL |  |
| b3_aqr | There were 397 car_exit events from the parking lot on December 8, 2025.... | PASS | PASS |  |

### L1_q012_crowd_events_expo
**Q:** How many crowd readings were taken on the expo floor today?
**Gold (sql):** 86400

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | There were 86,400 crowd readings taken on the expo floor today.... | PASS | PASS |  |
| b2_rag_cypher | There were 86,400 crowd readings taken on the expo floor today.... | PASS | PASS |  |
| b2_rag_hybrid | A total of 86,400 crowd readings were taken on the expo floor today. During the event, extensive CCTV coverage spanned m... | PASS | PASS |  |
| b3_aqr | There were 86,400 crowd readings taken on the expo floor today.... | PASS | PASS |  |

### L1_q013_total_car_entries
**Q:** In total, how many cars entered the venue today across all gates?
**Gold (sql):** 419

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | There were 419 car entry events recorded today across all gates.... | PASS | PASS |  |
| b2_rag_cypher | There were 419 car_entry events at the venue today across all gates.... | PASS | PASS |  |
| b2_rag_hybrid | A total of 419 cars entered the venue today across all gates. During the day, this activity was part of a broader set of... | PASS | PASS |  |
| b3_aqr | There were 419 car entry events at the venue today across all gates.... | PASS | PASS |  |

### L1_q014_people_at_intel_booth
**Q:** How many person entry events happened at the Intel demo booth area?
**Gold (sql):** 0

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | There were 0 person entry events at the Intel demo booth area on December 8, 2025.... | PASS | PASS |  |
| b2_rag_cypher | There were 0 person entry events at the Intel demo booth area on December 8, 2025.... | PASS | PASS |  |
| b2_rag_hybrid | There were zero person entry events at the Intel demo booth area. While the broader event context from community summari... | PASS | PASS |  |
| b3_aqr | There were 0 person entry events at the Intel demo booth area on December 8, 2025.... | PASS | PASS |  |

### L1_q015_food_court_crowd_readings
**Q:** How many times was the food court crowd measured today?
**Gold (sql):** 86400

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | There were 86,400 crowd measurements taken in the food court today.... | PASS | PASS |  |
| b2_rag_cypher | The food court crowd was not measured today.... | FAIL | FAIL |  |
| b2_rag_hybrid | The food court crowd was not measured at all today, as indicated by the Cypher row showing zero crowd samples. Despite t... | FAIL | FAIL |  |
| b3_aqr | The food court crowd was measured 86,400 times today.... | PASS | PASS |  |

### L1_q016_keynote_door_total_flow
**Q:** What was the total number of people going through the keynote hall door, both in and out?
**Gold (sql):** 1596

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The total number of people going through the keynote hall door, both in and out, was 1,596.... | PASS | PASS |  |
| b2_rag_cypher | A total of 0 people went through the keynote hall door on December 8, 2025.... | FAIL | FAIL |  |
| b2_rag_hybrid | The precise number of people going through the keynote hall door, both in and out, was zero according to the Cypher data... | FAIL | FAIL |  |
| b3_aqr | The total number of people going through the keynote hall door, both entering and exiting, was 1,596.... | PASS | PASS |  |

## L2 (15 questions)

### L2_q001_peak_headcount_nvidia_booth
**Q:** What was the peak head_count observed at DemoBooth_NVIDIA on 2025-12-08 (UTC)?
**Gold (sql):** 86

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The peak head_count observed at DemoBooth_NVIDIA on 2025-12-08 (UTC) was 86.... | PASS | PASS |  |
| b2_rag_cypher | The peak head_count observed at DemoBooth_NVIDIA on 2025-12-08 was 86.... | PASS | PASS |  |
| b2_rag_hybrid | The peak head count observed at DemoBooth_NVIDIA on December 8, 2025, was 86. This peak occurred amidst a bustling day a... | FAIL | FAIL |  |
| b3_aqr | The peak head_count observed at DemoBooth_NVIDIA on 2025-12-08 was 86.... | PASS | PASS |  |

### L2_q002_avg_headcount_foodcourt_lunch
**Q:** What was the average head_count at FoodCourt_North during lunch hours 12:00 to 14:00 UTC on 2025-12-08?
**Gold (sql):** 120.01

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The average head count at FoodCourt_North during lunch hours (12:00 to 14:00 UTC) on 2025-12-08 was approximately 120.01... | PASS | PASS |  |
| b2_rag_cypher | The average head count at FoodCourt_North during lunch hours (12:00 to 14:00 UTC) on 2025-12-08 was approximately 120.01... | PASS | PASS |  |
| b2_rag_hybrid | The average head count at FoodCourt_North during lunch hours (12:00 to 14:00 UTC) on December 8, 2025, was approximately... | FAIL | FAIL |  |
| b3_aqr | The average head_count at FoodCourt_North during lunch hours from 12:00 to 14:00 UTC on 2025-12-08 was 120.01.... | PASS | PASS |  |

### L2_q003_avg_confidence_all_events
**Q:** What was the average detection confidence across all events on 2025-12-08 (UTC)? Report to two decimal places.
**Gold (sql):** 0.9

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The average detection confidence across all events on 2025-12-08 (UTC) was 0.90.... | PASS | PASS |  |
| b2_rag_cypher | The average detection confidence across all events on 2025-12-08 (UTC) was 0.91.... | FAIL | FAIL |  |
| b2_rag_hybrid | The average detection confidence across all events on December 8, 2025 (UTC) was 0.91. This date experienced high levels... | FAIL | FAIL |  |
| b3_aqr | The average detection confidence across all events on 2025-12-08 (UTC) was 0.90.... | PASS | PASS |  |

### L2_q004_low_confidence_events_count
**Q:** How many events on 2025-12-08 (UTC) had a detection confidence below 0.85?
**Gold (sql):** 30467

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | There were 30,467 events on 2025-12-08 (UTC) with a detection confidence below 0.85.... | PASS | PASS |  |
| b2_rag_cypher | There were 231 events on 2025-12-08 (UTC) with a detection confidence below 0.85.... | FAIL | FAIL |  |
| b2_rag_hybrid | On December 8, 2025, there were 231 events recorded with a detection confidence below 0.85. This day featured significan... | FAIL | FAIL |  |
| b3_aqr | There were 30,467 events on 2025-12-08 (UTC) with a detection confidence below 0.85.... | PASS | PASS |  |

### L2_q005_net_person_flow_main_entrance
**Q:** What was the net person flow (person_entry events minus person_exit events) at Gate_MainEntrance on 2025-12-08 (UTC)?
**Gold (sql):** 179

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The net person flow at Gate_MainEntrance on 2025-12-08 (UTC) was 179.... | PASS | PASS |  |
| b2_rag_cypher | NO ANSWER... | ERR | FAIL | No answer generated |
| b2_rag_hybrid | The net person flow at Gate_MainEntrance on December 8, 2025, was 179, calculated as the difference between person entry... | FAIL | FAIL |  |
| b3_aqr | The net person flow at Gate_MainEntrance on 2025-12-08 (UTC) was 179.... | PASS | PASS |  |

### L2_q006_busiest_moment_nvidia
**Q:** How packed did the NVIDIA booth get at its busiest moment?
**Gold (sql):** 86

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The NVIDIA booth had its busiest moment at 16:48:47 UTC on December 8, 2025, with a headcount of 86 people, as recorded ... | FAIL | FAIL |  |
| b2_rag_cypher | The NVIDIA booth reached its busiest moment with a peak headcount of 86 people.... | PASS | PASS |  |
| b2_rag_hybrid | The NVIDIA booth experienced its busiest moment with a peak head count of 86 people. During the event, significant foot ... | PASS | PASS |  |
| b3_aqr | The NVIDIA booth was at its busiest with a head count of 86 people on December 8, 2025, at 16:48:47 UTC, as recorded by ... | PASS | PASS |  |

### L2_q007_low_confidence_detections
**Q:** How many detections had low confidence today, say below 85%?
**Gold (sql):** 30467

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | There were 30,467 low confidence detections today with confidence below 85%.... | PASS | PASS |  |
| b2_rag_cypher | There were 30,467 detections with low confidence below 85% today.... | PASS | PASS |  |
| b2_rag_hybrid | There were 30,467 detections with a confidence level below 85% today. Throughout the day, CCTV activity included a high ... | PASS | PASS |  |
| b3_aqr | There were 30,467 detections with confidence below 85% today.... | PASS | PASS |  |

### L2_q008_lunch_crowd_food_court
**Q:** How busy was the food court during lunch hours on average?
**Gold (sql):** 120.01

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The average head count in the food court during lunch hours on December 8, 2025, was approximately 81.87 people.... | FAIL | FAIL |  |
| b2_rag_cypher | The average head count at the food court during lunch hours was approximately 81.87.... | FAIL | FAIL |  |
| b2_rag_hybrid | The average head count during lunch hours at the food court was approximately 81.87 people. This bustling atmosphere was... | FAIL | FAIL |  |
| b3_aqr | During lunch hours at the food court, the average head count was 5.59 at 11 AM, 120.05 at noon, 119.97 at 1 PM, and 5.70... | FAIL | FAIL |  |

### L2_q009_min_crowd_keynote
**Q:** What was the quietest moment at the keynote stage — the lowest crowd count recorded?
**Gold (sql):** 0

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The quietest moment at the keynote stage was recorded at '2025-12-08T00:00:00Z' with a head count of 0.... | PASS | PASS |  |
| b2_rag_cypher | There were no crowd count records available for the Keynote Stage on December 8, 2025.... | FAIL | FAIL |  |
| b2_rag_hybrid | The quietest moment at the keynote stage, inferred from the community summaries, likely occurred during the timeframe fr... | FAIL | FAIL |  |
| b3_aqr | The quietest moment at the keynote stage was recorded at '2025-12-08T00:00:00Z' when the crowd count was 0.... | PASS | PASS |  |

### L2_q010_peak_expo_floor
**Q:** What was the biggest crowd the expo floor saw at any moment?
**Gold (sql):** 209

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The biggest crowd on the expo floor was 500 people, as recorded by camera CAM_07 at the KeynoteHall_Stage on 2025-12-08 ... | FAIL | FAIL |  |
| b2_rag_cypher | The biggest crowd the expo floor saw at any moment was 500 people.... | FAIL | FAIL |  |
| b2_rag_hybrid | The biggest crowd on the expo floor was 500 people at its peak. This occurred amidst a bustling backdrop of activity acr... | FAIL | FAIL |  |
| b3_aqr | The biggest crowd on the expo floor was 500 people, recorded at 'KeynoteHall_Stage' by camera 'CAM_07' on '2025-12-08T09... | FAIL | FAIL |  |

### L2_q011_avg_confidence_entries
**Q:** On average, how confident were the detections for people entering the main gate?
**Gold (sql):** 0.92

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | On average, the confidence level for detections of people entering the main gate was 0.915.... | PASS | PASS |  |
| b2_rag_cypher | On average, the confidence level for detections of people entering the main gate was 0.9150881776616587.... | PASS | PASS |  |
| b2_rag_hybrid | On average, the confidence level for detecting people entering the main gate was 91.51%. This high confidence level sugg... | FAIL | FAIL |  |
| b3_aqr | The average confidence for detections of people entering the main gate was 0.915.... | PASS | PASS |  |

### L2_q012_evening_crowd_food
**Q:** How crowded was the food court during dinner time, say 5 PM to 7 PM?
**Gold (sql):** 99.96

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The food court was quite crowded between 5 PM and 7 PM on December 8, 2025, with consistent head counts recorded around ... | FAIL | FAIL |  |
| b2_rag_cypher | The food court had an average head count of 100.1 people at 5 PM and 99.83 people at 6 PM. The peak head count was 119 p... | PASS | PASS |  |
| b2_rag_hybrid | During dinner time from 5 PM to 7 PM on December 8, 2025, the food court experienced significant activity. The average h... | FAIL | FAIL |  |
| b3_aqr | During dinner time, from 5 PM to 7 PM, at the Food Court North, the average head count was approximately 100 at 5 PM and... | FAIL | FAIL |  |

### L2_q013_max_people_one_hour_gate
**Q:** What was the most people that entered the main gate in any single hour?
**Gold (sql):** 334

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The most people that entered the main gate in any single hour on December 8, 2025, was 334 between 09:00 and 10:00 UTC.... | FAIL | FAIL |  |
| b2_rag_cypher | The most people that entered the main gate in any single hour was 334, during the hour starting at 09:00 UTC on December... | PASS | PASS |  |
| b2_rag_hybrid | The most people that entered the main gate in a single hour was 334, occurring between 09:00 and 09:59 UTC on December 8... | PASS | PASS |  |
| b3_aqr | The most people that entered the main gate in any single hour was 334, recorded at 09:00 on 2025-12-08.... | PASS | PASS |  |

### L2_q014_avg_intel_crowd
**Q:** What was the average crowd at the Intel booth throughout the day?
**Gold (sql):** 10.65

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The average crowd at the Intel booth throughout the day was approximately 10.65 people.... | PASS | PASS |  |
| b2_rag_cypher | The average crowd at the Intel booth throughout the day was approximately 10.65 people.... | PASS | PASS |  |
| b2_rag_hybrid | The average crowd at the Intel booth throughout the day was approximately 10.65 people. This activity took place within ... | PASS | PASS |  |
| b3_aqr | The average crowd at the Intel booth throughout the day was approximately 10.65 people.... | PASS | PASS |  |

### L2_q015_total_people_entered_venue
**Q:** Roughly how many people entered the venue in total today, counting all gates?
**Gold (sql):** 2601

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | A total of 2,601 people entered the venue today, counting all gates.... | PASS | PASS |  |
| b2_rag_cypher | A total of 2601 people entered the venue today.... | PASS | PASS |  |
| b2_rag_hybrid | A total of 2,601 people entered the venue today, counting all gates. This substantial influx reflects significant foot t... | PASS | PASS |  |
| b3_aqr | A total of 2,601 people entered the venue today through all gates.... | PASS | PASS |  |

## L3 (15 questions)

### L3_q001_peak_per_booth
**Q:** For each demo booth (DemoBooth_NVIDIA and DemoBooth_Intel), what was the peak head_count observed on 2025-12-08 (UTC)?
**Gold (sql):** [('DemoBooth_Intel', 53), ('DemoBooth_NVIDIA', 86)]

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The peak head count observed at DemoBooth_Intel on 2025-12-08 was 53. For DemoBooth_NVIDIA, the peak head count was 86.... | PASS | PASS |  |
| b2_rag_cypher | On 2025-12-08 (UTC), the peak head count observed at DemoBooth_Intel was 53, and at DemoBooth_NVIDIA, it was 86.... | PASS | PASS |  |
| b2_rag_hybrid | On December 8, 2025, the peak head count for DemoBooth_NVIDIA was 86, while DemoBooth_Intel saw a peak head count of 53.... | PASS | PASS |  |
| b3_aqr | The peak head count on 2025-12-08 for DemoBooth_NVIDIA was 86, and for DemoBooth_Intel, it was 53.... | PASS | PASS |  |

### L3_q002_event_counts_by_type
**Q:** For 2025-12-08 (UTC), how many events were recorded for each event_type? List every event_type with its count.
**Gold (sql):** [('car_entry', 419), ('car_exit', 427), ('crowd', 432000), ('person_entry', 2601), ('person_exit', 2493)]

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | On 2025-12-08 (UTC), the events recorded were: 419 for 'car_entry', 427 for 'car_exit', 432,000 for 'crowd', 2,601 for '... | PASS | PASS |  |
| b2_rag_cypher | For 2025-12-08 (UTC), the events recorded were: 419 car_entry events, 427 car_exit events, 432,000 crowd events, 2,601 p... | PASS | PASS |  |
| b2_rag_hybrid | On December 8, 2025 (UTC), the recorded event counts for each event type were as follows: 'car_entry' events totaled 419... | PASS | PASS |  |
| b3_aqr | On 2025-12-08, the following events were recorded: 419 car_entry events, 427 car_exit events, 432,000 crowd events, 2,60... | PASS | PASS |  |

### L3_q003_hourly_person_entry_main_entrance
**Q:** Show the hour-by-hour person_entry count at Gate_MainEntrance on 2025-12-08 (UTC). List each UTC hour (00 through 23) with its count.
**Gold (sql):** [('00', 13), ('01', 18), ('02', 8), ('03', 12), ('04', 8)]

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | Here is the hour-by-hour person entry count at Gate_MainEntrance on 2025-12-08 (UTC):  - 00: 00-01:00: 13 entries - 01: ... | PASS | PASS |  |
| b2_rag_cypher | Here is the hour-by-hour person entry count at Gate_MainEntrance on 2025-12-08 (UTC):  - 00:00: 13 - 01:00: 18 - 02:00: ... | PASS | PASS |  |
| b2_rag_hybrid | Here is the hour-by-hour person entry count at Gate_MainEntrance on December 8, 2025 (UTC):  - 00:00: 13 - 01:00: 18 - 0... | PASS | PASS |  |
| b3_aqr | Here is the hour-by-hour person entry count at Gate_MainEntrance on 2025-12-08 (UTC):  - 00:00: 13 - 01:00: 18 - 02:00: ... | PASS | PASS |  |

### L3_q004_avg_headcount_per_crowd_camera
**Q:** For each crowd-mode camera_location on 2025-12-08 (UTC), report the average head_count over the full day.
**Gold (sql):** [('DemoBooth_Intel', 10.65), ('DemoBooth_NVIDIA', 15.52), ('ExpoFloor_MainAisle', 49.36), ('FoodCourt_North', 23.07), ('KeynoteHall_Stage', 57.4)]

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | On 2025-12-08, the average head count for each crowd-mode camera location was as follows: DemoBooth_Intel had an average... | PASS | PASS |  |
| b2_rag_cypher | On 2025-12-08, the average head count at each crowd-mode camera location was as follows: 'DemoBooth_Intel' had 10.65, 'D... | PASS | PASS |  |
| b2_rag_hybrid | On December 8, 2025, the average head count at various camera locations was as follows: 'ExpoFloor_MainAisle' saw an ave... | PASS | PASS |  |
| b3_aqr | On 2025-12-08 (UTC), the average head count for each crowd-mode camera location was as follows: DemoBooth_Intel had 10.6... | PASS | PASS |  |

### L3_q005_top3_hours_by_crowd_activity
**Q:** What were the top 3 UTC hours on 2025-12-08 by total head_count summed across all crowd cameras? List the hour and its total head_count for each of the top 3.
**Gold (sql):** [('16', 2365493), ('14', 2059433), ('09', 1685871)]

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The top 3 UTC hours on 2025-12-08 by total head_count summed across all crowd cameras were: 1. Hour 16 with a total head... | PASS | PASS |  |
| b2_rag_cypher | The top 3 UTC hours on 2025-12-08 by total head_count were:  1. 16:00 with a total head_count of 657.08 2. 14:00 with a ... | FAIL | REVIEW | Needs manual check |
| b2_rag_hybrid | On December 8, 2025, the top three UTC hours by total head count across all crowd cameras were as follows:   1. 16:00 UT... | FAIL | REVIEW | Needs manual check |
| b3_aqr | The top 3 UTC hours on 2025-12-08 by total head count summed across all crowd cameras were: 16:00 with a total head coun... | FAIL | REVIEW | Needs manual check |

### L3_q006_arrival_pattern_main_gate
**Q:** Show me when people were arriving at the main entrance throughout the day, broken down hour by hour.
**Gold (sql):** [('00', 13), ('01', 18), ('02', 8), ('03', 12), ('04', 8)]

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | Here is the hourly breakdown of people arriving at the main entrance on December 8, 2025:  - 00:00-01:00: 13 arrivals - ... | PASS | PASS |  |
| b2_rag_cypher | Throughout December 8, 2025, at the main entrance, the highest number of people arrived during the 09:00-10:00 hour with... | FAIL | REVIEW | Needs manual check |
| b2_rag_hybrid | Throughout December 8, 2025, people arrived at the main entrance in varying numbers hour by hour. The highest influx was... | FAIL | REVIEW | Needs manual check |
| b3_aqr | Throughout December 8, 2025, people arrived at the main entrance most frequently between 08:00 and 09:00 UTC with 311 en... | FAIL | REVIEW | Needs manual check |

### L3_q007_crowd_hotspots
**Q:** Which areas of the venue had the most crowd activity? Rank them by their average crowd size.
**Gold (sql):** [('KeynoteHall_Stage', 57.4), ('ExpoFloor_MainAisle', 49.36), ('FoodCourt_North', 23.07), ('DemoBooth_NVIDIA', 15.52), ('DemoBooth_Intel', 10.65)]

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The areas of the venue ranked by their average crowd size, from most to least, are: KeynoteHall_Stage with an average cr... | PASS | PASS |  |
| b2_rag_cypher | The Keynote Hall Stage had the most crowd activity with an average crowd size of 57.3975. It is followed by the Expo Flo... | FAIL | REVIEW | Needs manual check |
| b2_rag_hybrid | The areas of the venue with the most crowd activity, ranked by their average crowd size, are as follows: KeynoteHall_Sta... | PASS | PASS |  |
| b3_aqr | The area with the most crowd activity was 'KeynoteHall_Stage', with an average crowd size of 57.40. It was followed by '... | PASS | PASS |  |

### L3_q008_event_volume_by_hour
**Q:** How does activity change throughout the day across the whole venue? Show the total number of events per hour.
**Gold (sql):** [('00', 18040), ('01', 18039), ('02', 18029), ('03', 18032), ('04', 18036)]

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | Activity throughout the venue on December 8th, 2025, varied by the hour. The period between 07:00 and 09:00 UTC experien... | FAIL | REVIEW | Needs manual check |
| b2_rag_cypher | Activity at the venue varies throughout the day, with the number of events ranging from 18029 to 19292 per hour. The hig... | FAIL | REVIEW | Needs manual check |
| b2_rag_hybrid | Throughout the day, activity at the venue varied, peaking around distinct hours. According to the precise counts, the mo... | FAIL | REVIEW | Needs manual check |
| b3_aqr | The total number of events per hour across the venue on December 8, 2025, shows a consistent activity level throughout t... | FAIL | REVIEW | Needs manual check |

### L3_q009_crowd_surge_timeline
**Q:** Show me how the crowd size changed at the keynote stage throughout the day — give me the average crowd for each hour.
**Gold (sql):** [('00', 7.0), ('01', 7.3), ('02', 7.1), ('03', 7.2), ('04', 7.0)]

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | Throughout the day at the keynote stage, major crowd size increases are noted during the 9 AM, 2 PM, and 4 PM hours with... | FAIL | REVIEW | Needs manual check |
| b2_rag_cypher | No crowd data was recorded for the keynote stage on December 8, 2025.... | FAIL | REVIEW | Needs manual check |
| b2_rag_hybrid | Throughout the day at the keynote stage, crowd size varied significantly. Initially, between 08:00 and 15:59 UTC, there ... | FAIL | REVIEW | Needs manual check |
| b3_aqr | There is no data available for the average crowd size at the keynote stage for the specified date, as no rows were retur... | FAIL | FAIL | Claims no data exists — incorrect |

### L3_q010_entry_exit_balance
**Q:** For each gate, how many people came in versus how many went out during the day? I want to see if the numbers balance.
**Gold (sql):** [('Gate_MainEntrance', 1569, 1382), ('Gate_ParkingLot', 669, 724), ('KeynoteHall_DoorA', 782, 814)]

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | At 'Gate_MainEntrance', 1,531 people entered and 1,352 exited. At 'Gate_ParkingLot', 288 people entered and 327 exited. ... | FAIL | REVIEW | Needs manual check |
| b2_rag_cypher | At 'Gate_MainEntrance', there were 1,531 people entries and 1,352 exits. For 'Gate_ParkingLot', there were 288 entries a... | FAIL | REVIEW | Needs manual check |
| b2_rag_hybrid | At the Gate_MainEntrance, 1,531 people entered while 1,352 exited, showing more entries than exits by 179. For Gate_Park... | FAIL | REVIEW | Needs manual check |
| b3_aqr | At 'Gate_MainEntrance', 1,531 people entered and 1,352 people exited. At 'Gate_ParkingLot', there were 288 entries and 3... | FAIL | REVIEW | Needs manual check |

### L3_q011_busiest_camera_per_hour
**Q:** For each hour of the day, which camera location had the highest crowd? Show me the winning location and its average crowd size for each hour.
**Gold (sql):** [('00', 'KeynoteHall_Stage', 7.0), ('01', 'KeynoteHall_Stage', 7.3), ('02', 'KeynoteHall_Stage', 7.1), ('03', 'KeynoteHall_Stage', 7.2), ('04', 'KeynoteHall_Stage', 7.0)]

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | Here are the camera locations with the highest average crowd size for each hour on December 8, 2025:  - 00:00 - KeynoteH... | PASS | PASS |  |
| b2_rag_cypher | For each hour on December 8, 2025, the camera location with the highest average crowd size was as follows:  - 00:00 - 08... | FAIL | REVIEW | Needs manual check |
| b2_rag_hybrid | Throughout the day on December 8, 2025, different camera locations observed varying levels in crowd size. During the lat... | FAIL | REVIEW | Needs manual check |
| b3_aqr | For each hour on December 8, 2025, the location with the highest average crowd size was generally "KeynoteHall_Stage" du... | FAIL | REVIEW | Needs manual check |

### L3_q012_car_traffic_by_hour
**Q:** Break down the car traffic at the parking lot by hour — entries and exits separately.
**Gold (sql):** [('00', 'car_exit', 4), ('01', 'car_exit', 4), ('02', 'car_entry', 1), ('02', 'car_exit', 2), ('03', 'car_entry', 2)]

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The breakdown by hour for car traffic at the parking lot on December 8, 2025, is as follows:  - Midnight to 1 AM: 0 entr... | FAIL | FAIL | Claims no data exists — incorrect |
| b2_rag_cypher | There were no car entry or exit events recorded at the parking lot on December 8, 2025.... | FAIL | REVIEW | Needs manual check |
| b2_rag_hybrid | Over the course of December 8, 2025, car traffic in the parking lot displayed a noticeable pattern. From 07:00 to 18:59 ... | FAIL | REVIEW | Needs manual check |
| b3_aqr | There were no car entry or car exit events detected at the parking lot on December 8, 2025.... | FAIL | REVIEW | Needs manual check |

### L3_q013_nvidia_hourly_crowd
**Q:** Give me the NVIDIA booth's crowd numbers hour by hour.
**Gold (sql):** [('00', 3.5), ('01', 3.5), ('02', 3.5), ('03', 3.5), ('04', 3.6)]

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | Here are the crowd numbers for the NVIDIA booth on December 8, 2025, hour by hour (UTC time):  - 00:00: 12,493 - 01:00: ... | FAIL | REVIEW | Needs manual check |
| b2_rag_cypher | On December 8, 2025, the average head count at the NVIDIA booth increased significantly during typical midday hours. Spe... | FAIL | REVIEW | Needs manual check |
| b2_rag_hybrid | The NVIDIA booth experienced varying crowd numbers throughout December 8, 2025. During early morning hours (midnight to ... | FAIL | REVIEW | Needs manual check |
| b3_aqr | Here are the crowd numbers hour by hour for the NVIDIA booth on December 8, 2025:  - 00:00 UTC: Average 3.47, Peak 16 - ... | PASS | PASS |  |

### L3_q014_all_gates_person_flow
**Q:** For each gate location, give me the total number of people who entered and exited.
**Gold (sql):** [('Gate_MainEntrance', 'person_entry', 1531), ('Gate_MainEntrance', 'person_exit', 1352), ('Gate_ParkingLot', 'person_entry', 288), ('Gate_ParkingLot', 'person_exit', 327), ('KeynoteHall_DoorA', 'pers

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | At the Gate_MainEntrance, there were 1,531 people who entered and 1,352 people who exited. At the Gate_ParkingLot, there... | FAIL | REVIEW | Needs manual check |
| b2_rag_cypher | At Gate_MainEntrance, there were 1,531 people entries and 1,352 people exits. At Gate_ParkingLot, there were 288 people ... | FAIL | REVIEW | Needs manual check |
| b2_rag_hybrid | For the Gate_MainEntrance, a total of 1,531 people entered and 1,352 exited. At the Gate_ParkingLot, 288 people entered ... | FAIL | REVIEW | Needs manual check |
| b3_aqr | At the "Gate_MainEntrance" location, there were 1,531 person entries and 1,352 person exits. At the "Gate_ParkingLot" lo... | FAIL | REVIEW | Needs manual check |

### L3_q015_peak_crowd_each_location
**Q:** What was the peak crowd at each location across the venue?
**Gold (sql):** [('KeynoteHall_Stage', 500), ('ExpoFloor_MainAisle', 209), ('FoodCourt_North', 146), ('DemoBooth_NVIDIA', 86), ('DemoBooth_Intel', 53)]

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The peak crowds at each location across the venue on December 8, 2025, were as follows: DemoBooth_Intel saw 53 people, D... | PASS | PASS |  |
| b2_rag_cypher | The peak crowd at each location was as follows: DemoBooth_Intel had 53, DemoBooth_NVIDIA had 86, ExpoFloor_MainAisle had... | PASS | PASS |  |
| b2_rag_hybrid | The peak crowd at each location across the venue were as follows: DemoBooth_Intel had a peak of 53 people, DemoBooth_NVI... | PASS | PASS |  |
| b3_aqr | The peak crowd at each location across the venue was as follows: DemoBooth_Intel had a peak crowd of 53, DemoBooth_NVIDI... | PASS | PASS |  |

## L4 (15 questions)

### L4_q001_compare_booths
**Q:** On 2025-12-08 (UTC), compare the crowd activity at DemoBooth_NVIDIA versus DemoBooth_Intel. Which booth was busier, and approximately what was the ratio of their average head_counts?
**Gold (structured_facts):** {'busier_booth': 'DemoBooth_NVIDIA', 'average_headcount_ratio_nvidia_over_intel': {'value': 1.4, 'tolerance': 0.4}}

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | On 2025-12-08, the DemoBooth_NVIDIA was busier than DemoBooth_Intel, with an average head count of 15.52 compared to 10.... | PASS | PASS |  |
| b2_rag_cypher | On 2025-12-08 (UTC), DemoBooth_NVIDIA was busier than DemoBooth_Intel, with an average head count of 15.52 compared to I... | PASS | PASS |  |
| b2_rag_hybrid | On December 8, 2025, the DemoBooth_NVIDIA was busier than DemoBooth_Intel, with an average head count of approximately 1... | PASS | PASS |  |
| b3_aqr | On 2025-12-08 (UTC), DemoBooth_NVIDIA was busier than DemoBooth_Intel. The average headcount at DemoBooth_NVIDIA was 15.... | FAIL | REVIEW | Needs manual check |

### L4_q002_gate_flow_comparison
**Q:** On 2025-12-08 (UTC), which gate had higher total person flow (person_entry + person_exit combined) — Gate_MainEntrance or Gate_ParkingLot? State which gate and their approximate totals.
**Gold (structured_facts):** {'higher_flow_gate': 'Gate_MainEntrance', 'gate_mainentrance_flow_approx': {'value': 2900, 'tolerance': 400}, 'gate_parkinglot_flow_approx': {'value': 620, 'tolerance': 150}}

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | Gate_MainEntrance had a higher total person flow on 2025-12-08, with approximately 2883 entries and exits combined, comp... | PASS | PASS |  |
| b2_rag_cypher | On 2025-12-08 (UTC), Gate_MainEntrance had the higher total person flow with approximately 2883 combined person_entry an... | FAIL | REVIEW | Needs manual check |
| b2_rag_hybrid | On December 8, 2025, the Gate_MainEntrance had a significantly higher total person flow compared to the Gate_ParkingLot.... | PASS | PASS |  |
| b3_aqr | Gate_MainEntrance had the higher total person flow with 2,883 combined person_entry and person_exit events, while Gate_P... | PASS | PASS |  |

### L4_q003_morning_vs_evening_main_entrance
**Q:** On 2025-12-08 (UTC), compare the morning rush window (08:00-10:00) versus the evening rush window (17:00-19:00) at Gate_MainEntrance for total person flow (person_entry + person_exit). Which window was busier and approximately by how much?
**Gold (structured_facts):** {'busier_window': '08:00', 'morning_total_approx': {'value': 1200, 'tolerance': 250}, 'evening_total_approx': {'value': 1000, 'tolerance': 250}}

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The morning rush window at Gate_MainEntrance was busier with a total person flow of 1,191, compared to the evening rush ... | FAIL | REVIEW | Needs manual check |
| b2_rag_cypher | On 2025-12-08 at Gate_MainEntrance, the morning rush window (08:00-10:00) was busier with a total person flow of 1,191 c... | PASS | PASS |  |
| b2_rag_hybrid | On December 8, 2025, the morning rush window (08:00-10:00) at Gate_MainEntrance was busier than the evening rush window ... | PASS | PASS |  |
| b3_aqr | The morning rush window (08:00-10:00) was busier at Gate_MainEntrance with a total person flow of 1,191 compared to the ... | PASS | PASS |  |

### L4_q004_keynote_morning_vs_afternoon
**Q:** Compare the average head_count at KeynoteHall_Stage between the morning keynote window 09:00-10:00 UTC and the afternoon keynote window 14:00-15:00 UTC on 2025-12-08. Which keynote had higher attendance and what were the approximate average head_counts?
**Gold (structured_facts):** {'higher_attendance_window': 'morning', 'morning_keynote_avg_approx': {'value': 450, 'tolerance': 80}, 'afternoon_keynote_avg_approx': {'value': 400, 'tolerance': 80}}

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The morning keynote at KeynoteHall_Stage had higher attendance with an average head count of approximately 450.19. In co... | PASS | PASS |  |
| b2_rag_cypher | On 2025-12-08, the morning keynote at KeynoteHall_Stage had a higher average attendance with an approximate average head... | PASS | PASS |  |
| b2_rag_hybrid | On December 8, 2025, the average head_count at KeynoteHall_Stage was higher during the morning keynote window from 09:00... | PASS | PASS |  |
| b3_aqr | The morning keynote at KeynoteHall_Stage on 2025-12-08 had higher attendance, with an approximate average head_count of ... | PASS | PASS |  |

### L4_q005_highest_peak_to_baseline_ratio
**Q:** Across all crowd-mode cameras (ExpoFloor_MainAisle, DemoBooth_NVIDIA, DemoBooth_Intel, KeynoteHall_Stage, FoodCourt_North) on 2025-12-08 (UTC), which location showed the most extreme peak-to-baseline contrast — meaning the largest ratio of its peak head_count to its overnight quiet-hour average head_count? Identify the camera_location and explain the ratio order of magnitude.
**Gold (structured_facts):** {'most_extreme_location': 'KeynoteHall_Stage'}

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The location with the most extreme peak-to-baseline contrast on 2025-12-08 was "KeynoteHall_Stage," with a peak-to-basel... | PASS | PASS |  |
| b2_rag_cypher | The location with the most extreme peak-to-baseline contrast was the "KeynoteHall_Stage" camera. The peak head_count was... | PASS | PASS |  |
| b2_rag_hybrid | The location with the most extreme peak-to-baseline contrast in head count on December 8, 2025, was the KeynoteHall_Stag... | PASS | PASS |  |
| b3_aqr | The location with the most extreme peak-to-baseline contrast on 2025-12-08 (UTC) was KeynoteHall_Stage, showing a ratio ... | PASS | PASS |  |

### L4_q006_morning_vs_evening_rush
**Q:** Was the morning rush bigger than the evening rush at the main entrance, in terms of how many people came and went?
**Gold (structured_facts):** {'bigger_rush': 'morning', 'morning_total_approx': {'value': 1200, 'tolerance': 250}, 'evening_total_approx': {'value': 1000, 'tolerance': 250}}

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The morning rush at the main entrance was bigger than the evening rush. There were 1,236 people events in the morning co... | PASS | PASS |  |
| b2_rag_cypher | Yes, the morning rush was bigger than the evening rush at the main entrance. There were 1,277 people entries and exits i... | PASS | PASS |  |
| b2_rag_hybrid | The morning rush at the main entrance was indeed larger than the evening rush in terms of total flow. The morning period... | PASS | PASS |  |
| b3_aqr | The morning rush at the main entrance saw more people come and go, with a total flow of 1,277, compared to the evening r... | PASS | PASS |  |

### L4_q007_nvidia_vs_intel_booth_attraction
**Q:** Which demo booth attracted bigger crowds — NVIDIA or Intel? Roughly how much more popular was the winner?
**Gold (structured_facts):** {'winner': 'NVIDIA', 'intel_mentioned': 'Intel'}

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The NVIDIA demo booth attracted a bigger crowd, with a total head count of 1,340,536. It was roughly 420,537 more popula... | PASS | PASS |  |
| b2_rag_cypher | Both the NVIDIA and Intel demo booths attracted the same size crowds, with each having a total crowd count of 86,400. Ne... | PASS | PASS |  |
| b2_rag_hybrid | Both the NVIDIA and Intel demo booths attracted the same crowd size of 86,400 individuals each during the recorded perio... | PASS | PASS |  |
| b3_aqr | Both the NVIDIA and Intel demo booths attracted the same size crowd, with each having a total of 86,400 attendees over t... | PASS | PASS |  |

### L4_q008_keynote_attendance_dropoff
**Q:** Did the keynote stage attendance drop off later in the day, or stay similar across the morning and afternoon keynotes?
**Gold (structured_facts):** {'trend_keyword_a': 'morning', 'trend_keyword_b': 'afternoon'}

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The keynote stage attendance was significantly higher during the morning at 09:00 with a total head count of 1,620,671 a... | PASS | PASS |  |
| b2_rag_cypher | There is no data available for the keynote stage attendance on December 8, 2025. Therefore, it is not possible to determ... | FAIL | FAIL | Claims no data exists — incorrect |
| b2_rag_hybrid | The keynote stage attendance exhibited a noticeable pattern throughout the day on December 8, 2025. Early in the day, fr... | PASS | PASS |  |
| b3_aqr | There is no available data on the keynote stage attendance for December 8, 2025.... | FAIL | REVIEW | Needs manual check |

### L4_q009_object_tracking_cross_camera
**Q:** Were there any tracked objects (by object_id) that were detected at Gate_MainEntrance AND also at KeynoteHall_DoorA on 2025-12-08? If so, how many unique objects appeared at both locations?
**Gold (sql):** 1564

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | There were 1,596 unique objects detected at both Gate_MainEntrance and KeynoteHall_DoorA on 2025-12-08.... | FAIL | REVIEW | Needs manual check |
| b2_rag_cypher | There were 1,596 unique objects detected at both Gate_MainEntrance and KeynoteHall_DoorA on 2025-12-08.... | FAIL | REVIEW | Needs manual check |
| b2_rag_hybrid | Yes, there were 1,596 unique objects detected at both Gate_MainEntrance and KeynoteHall_DoorA on December 8, 2025. The a... | FAIL | REVIEW | Needs manual check |
| b3_aqr | There were 1,596 unique objects detected at both Gate_MainEntrance and KeynoteHall_DoorA on 2025-12-08.... | FAIL | REVIEW | Needs manual check |

### L4_q010_camera_correlation
**Q:** Which two crowd camera locations had the most similar hourly activity patterns on 2025-12-08? Compare all pairs of crowd cameras by how closely their hourly average head_counts track each other.
**Gold (structured_facts):** {'most_similar_pair_includes': 'DemoBooth'}

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The crowd camera locations "DemoBooth_Intel" and "DemoBooth_NVIDIA" had the most similar hourly activity patterns on 202... | PASS | PASS |  |
| b2_rag_cypher | The two crowd camera locations with the most similar hourly activity patterns on 2025-12-08 were "DemoBooth_Intel" and "... | PASS | PASS |  |
| b2_rag_hybrid | Based on the community summaries, the crowd cameras likely to have the most similar hourly activity patterns on December... | FAIL | FAIL | No answer generated |
| b3_aqr | The crowd camera locations 'DemoBooth_NVIDIA' and 'DemoBooth_Intel' had the most similar hourly activity patterns on 202... | PASS | PASS |  |

### L4_q011_people_flow_gate_to_keynote
**Q:** Did people who came through the main entrance also show up at the keynote? How many people were tracked at both locations compared to just the main entrance?
**Gold (structured_facts):** {'overlap_exists': 'yes', 'main_entrance_mentioned': 'Gate_MainEntrance'}

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | 409 people were tracked at both the main entrance and the keynote. In comparison, 1,122 people were tracked only at the ... | FAIL | REVIEW | Needs manual check |
| b2_rag_cypher | Yes, people who came through the main entrance also showed up at the keynote. There were 1,531 people tracked at the mai... | FAIL | REVIEW | Needs manual check |
| b2_rag_hybrid | A total of 409 people were tracked at both the main entrance and the keynote, according to the precise data. Comparative... | FAIL | REVIEW | Needs manual check |
| b3_aqr | No people who came through the main entrance were tracked at both the main entrance and the keynote location. There were... | FAIL | REVIEW | Needs manual check |

### L4_q012_crowd_before_after_keynote
**Q:** Was the expo floor busier before the morning keynote or after it? Compare the average crowd at the expo floor during 07:00-09:00 versus 10:00-12:00.
**Gold (structured_facts):** {'busier_window': '10:00', 'after_keynote_higher': 'after'}

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The expo floor was significantly busier after the morning keynote. The average crowd was about 5.6 people during 07:00-0... | PASS | PASS |  |
| b2_rag_cypher | The expo floor was significantly busier after the morning keynote. The average crowd between 07:00 and 09:00 was 5.605, ... | PASS | PASS |  |
| b2_rag_hybrid | The expo floor was significantly busier after the morning keynote than before it. From 07:00 to 09:00, the average crowd... | PASS | PASS |  |
| b3_aqr | The expo floor was significantly busier after the morning keynote, with an average crowd of 179.94 during 10:00-12:00, c... | PASS | PASS |  |

### L4_q013_food_court_vs_expo_lunch
**Q:** During lunch hours (12-14), did the food court get more crowded than the expo floor, or did people stay at the booths? Compare the average crowd sizes.
**Gold (structured_facts):** {'food_court_mentioned': 'FoodCourt', 'expo_mentioned': 'Expo'}

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | During lunch hours, the Food Court North had an average crowd size of approximately 120.01, which is larger than both th... | FAIL | REVIEW | Needs manual check |
| b2_rag_cypher | During lunch hours, the expo floor was more crowded than the food court. The average crowd size on the ExpoFloor_MainAis... | PASS | PASS |  |
| b2_rag_hybrid | During lunch hours, the Expo Floor Main Aisle was notably more crowded than the Food Court North, with an average crowd ... | FAIL | REVIEW | Needs manual check |
| b3_aqr | During lunch hours, the Expo Floor was more crowded than the Food Court, with an average crowd size of 108.55 compared t... | FAIL | REVIEW | Needs manual check |

### L4_q014_parking_car_person_ratio
**Q:** At the parking lot gate, what's the ratio of car traffic to pedestrian traffic? Are more cars coming through or more people walking?
**Gold (structured_facts):** {'parking_lot_mentioned': 'Parking'}

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | At the parking lot gate on the specified date, there were 778 car traffic events and 288 pedestrian traffic events. The ... | PASS | PASS |  |
| b2_rag_cypher | There were 0 car traffic events and 0 pedestrian traffic events at the parking lot gate on December 8, 2025. The traffic... | PASS | PASS |  |
| b2_rag_hybrid | Based on the Cypher data, there is an equal amount of car and pedestrian traffic at the parking lot gate, as both total ... | PASS | PASS |  |
| b3_aqr | There was an equal amount of car traffic and pedestrian traffic at the parking lot gate on December 8, 2025.... | PASS | PASS |  |

### L4_q015_quiet_vs_busy_locations
**Q:** Which location was the quietest and which was the busiest in terms of average crowd? How big is the gap?
**Gold (structured_facts):** {'busiest': 'KeynoteHall_Stage', 'quietest': 'DemoBooth_Intel'}

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The quietest location was "DemoBooth_Intel" with an average head count of 10.65. The busiest location was "KeynoteHall_S... | PASS | PASS |  |
| b2_rag_cypher | The quietest location was "DemoBooth_Intel" with an average crowd of 10.65, and the busiest location was "KeynoteHall_St... | PASS | PASS |  |
| b2_rag_hybrid | The quietest location in terms of average crowd was DemoBooth_Intel, with an average of approximately 10.65 people. In c... | PASS | PASS |  |
| b3_aqr | The quietest location was "DemoBooth_Intel," and the busiest was "KeynoteHall_Stage." The gap in average crowd size betw... | PASS | PASS |  |

## L5 (15 questions)

### L5_q001_summit_day_brief
**Q:** Write a security and operations brief for the AI Hardware Summit on 2025-12-08 (UTC). Cover: the busiest traffic windows at the main gates, keynote hall attendance peaks, lunchtime dynamics at the food court, and how the demo booths (NVIDIA and Intel) compared in crowd activity. Keep it to 5 bullet points.
**Gold (rubric_coverage):** Gate_MainEntrance shows morning person-entry peak around 08-10 UTC | Gate_MainEntrance shows evening person-exit peak around 17-19 UTC | KeynoteHall_Stage crowd peaks during keynote hours (09-10 UTC a

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | - The busiest traffic windows at the main gates occurred from 08:00 to 09:00 UTC with 607 and 601 events, respectively, ... | PASS | PASS |  |
| b2_rag_cypher | - **Busiest Traffic Windows:** The main gates experienced peak traffic at 8:00 UTC with 607 events, 9:00 UTC with 601 ev... | PASS | PASS |  |
| b2_rag_hybrid | - **Main Gate Traffic Busiest Windows**: The main entrance experienced its highest traffic from 08:00 to 09:00 UTC, with... | PASS | PASS |  |
| b3_aqr | - **Busiest Traffic Windows at Main Gates:** The busiest period at the main entrance occurred from 08:00 to 12:59 UTC, w... | PASS | PASS |  |

### L5_q002_nvidia_booth_timeline
**Q:** Describe the full-day activity timeline at DemoBooth_NVIDIA on 2025-12-08 (UTC). Identify the busiest time windows, any lulls, and quantify the peak crowd sizes versus the baseline. Write 3-5 sentences.
**Gold (rubric_coverage):** Morning peak between 10-12 UTC | Afternoon peak between 15-17 UTC | Lunch-hour dip (around 12-13 or 13-14 UTC) | Peak head_count values are substantially higher than baseline of ~3 | Overnight / early

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | On 2025-12-08, the activity at DemoBooth_NVIDIA was highest between 15:00 and 16:00 UTC, with a peak head count of 252,4... | PASS | PASS |  |
| b2_rag_cypher | On December 8, 2025, the DemoBooth_NVIDIA experienced its busiest periods during 10:00-11:00 UTC and 15:00-16:00 UTC, wi... | PASS | PASS |  |
| b2_rag_hybrid | On December 8, 2025, the activity timeline at the DemoBooth_NVIDIA showed distinct variances throughout the day. The bus... | PASS | PASS |  |
| b3_aqr | On December 8, 2025, at DemoBooth_NVIDIA, activity fluctuated throughout the day. The busiest periods were between 10:00... | PASS | PASS |  |

### L5_q003_staffing_brief
**Q:** Write a staffing recommendation brief for the AI Hardware Summit on 2025-12-08 (UTC). Identify (a) the busiest hours of the day requiring extra staff at the gates and on the expo floor, and (b) the quiet hours where minimal coverage is sufficient. Cite specific hour ranges and supporting metrics. Keep it to 4-6 bullet points.
**Gold (rubric_coverage):** Morning gate rush around 08:00-10:00 UTC needs extra staffing | Evening gate rush around 17:00-19:00 UTC needs extra staffing | Lunch hours 12:00-14:00 UTC are busy at FoodCourt and need extra coverag

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | - **Busiest Hours:**   - From 15:00 to 17:00 at 'DemoBooth_NVIDIA' with a total head count of 251,999 at 15:00 and 252,4... | FAIL | REVIEW | Needs manual check |
| b2_rag_cypher | - **Busiest Hours (Extra Staff Needed):**   - **08:00 - 09:59** UTC: Highest activity with 19,292 events at 08:00 and 19... | PASS | PASS |  |
| b2_rag_hybrid | - **Busiest Hours Requiring Extra Staff:**   - **08:00 - 09:59 UTC:** Significant activity with total events peaking at ... | FAIL | REVIEW | Needs manual check |
| b3_aqr | - **Busiest Hours for Staffing:**   - **08:00 - 09:00 UTC**: The highest event volume with 19,292 recorded events, suppo... | FAIL | REVIEW | Needs manual check |

### L5_q004_security_attention_report
**Q:** Produce a security-attention report for 2025-12-08 (UTC) at the AI Hardware Summit. Identify the locations and time windows that warrant the most security focus based on volume of activity. Specifically highlight (1) the gate that handles the largest volume of person traffic, (2) the gate with the most car traffic, and (3) the public area with the highest crowd density spikes. Quantify each with approximate numbers and times.
**Gold (rubric_coverage):** Gate_MainEntrance handles the largest person traffic volume | Gate_ParkingLot handles the most car traffic | KeynoteHall_Stage shows the highest crowd density spikes (head_counts in the hundreds) | Pe

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | On December 8, 2025, the gate handling the largest volume of person traffic was Gate_MainEntrance at 08:00, with approxi... | PASS | PASS |  |
| b2_rag_cypher | NO ANSWER... | ERR | FAIL | No answer generated |
| b2_rag_hybrid | On December 8, 2025, at the AI Hardware Summit, security attention should be emphasized at several locations based on th... | PASS | PASS |  |
| b3_aqr | On December 8, 2025, during the AI Hardware Summit, the Gate_MainEntrance experienced the largest volume of person traff... | PASS | PASS |  |

### L5_q005_keynote_hall_lifecycle
**Q:** Describe the full lifecycle of activity at the keynote hall on 2025-12-08 (UTC). Cover: (a) door entry patterns at KeynoteHall_DoorA throughout the day, (b) the in-hall crowd density at KeynoteHall_Stage during keynote sessions, and (c) how the post-keynote dispersal compares to pre-keynote build-up. Use specific hours and numbers from the data. 4-6 sentences.
**Gold (rubric_coverage):** KeynoteHall_DoorA shows entry peaks aligned with keynote start times (around 08:00-10:00, 13:00-14:00, or 15:00-16:00 UTC) | KeynoteHall_Stage crowd peaks during the keynote sessions, reaching head_co

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | On 2025-12-08, entry patterns at KeynoteHall_DoorA showed significant activity in the morning, with 186 entries between ... | PASS | PASS |  |
| b2_rag_cypher | On 2025-12-08, door entry patterns at KeynoteHall_DoorA showed significant entry spikes at 08:00 with 186 entries and at... | PASS | PASS |  |
| b2_rag_hybrid | On December 8, 2025, activity at the KeynoteHall_DoorA commenced at around 08:00 UTC, with notable morning entries total... | PASS | PASS |  |
| b3_aqr | On December 8, 2025, activity at KeynoteHall_DoorA saw a distinct pattern, with an initial build-up starting at 08:00 UT... | PASS | PASS |  |

### L5_q006_how_did_the_day_go
**Q:** Tell me how the day went at the conference — what stood out, when were the big moments, and what does the activity tell us?
**Gold (rubric_coverage):** Significant person traffic at the main entrance, especially in the morning and evening | Keynote sessions drew large crowds at the keynote stage area | Demo booths (especially NVIDIA) had notable crow

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | On December 8, 2025, the most significant moments at the conference occurred in the Keynote Hall at 9:00 AM, 2:00 PM, an... | FAIL | REVIEW | Needs manual check |
| b2_rag_cypher | The conference on December 8, 2025, saw a number of significant activity spikes throughout the day. Key moments included... | PASS | PASS |  |
| b2_rag_hybrid | The conference day was vibrant and bustling, with significant crowd activity noted across various locations. Key moments... | FAIL | FAIL | No answer generated |
| b3_aqr | The conference saw an overall smooth flow of attendees throughout the day, punctuated by several standout periods. Notab... | FAIL | REVIEW | Needs manual check |

### L5_q007_security_team_handoff
**Q:** If you were running security here, what would you tell your team based on the day's activity? Where should we keep the most eyes, and when do we need extra hands?
**Gold (rubric_coverage):** Main entrance is the highest-traffic location and needs constant attention | Crowd-management focus on keynote area during keynote hours | Extra coverage needed during morning arrival window and eveni

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | Based on today's activity, significant attention should be focused on the KeynoteHall_Stage at 09:00, which recorded the... | PASS | PASS |  |
| b2_rag_cypher | NO ANSWER... | ERR | FAIL | No answer generated |
| b2_rag_hybrid | For the day's security focus, attention should be concentrated predominantly at the Gate_MainEntrance during the morning... | PASS | PASS |  |
| b3_aqr | Based on today's CCTV activity, focus your team's surveillance on the ExpoFloor_MainAisle, particularly in the morning h... | FAIL | REVIEW | Needs manual check |

### L5_q008_what_should_change
**Q:** Looking at how this conference day played out, what could be improved next time — staffing, layout, scheduling? Give me your top recommendations grounded in what the data shows.
**Gold (rubric_coverage):** Lunch-hour congestion at the food court suggests adding capacity or staggered breaks | Concentrated rush hours at the main entrance suggest staggered start times or additional lanes | Significant peak

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The data suggests that the peak hour of activity during the conference was 08:00, with 19,292 events and a headcount of ... | FAIL | REVIEW | Needs manual check |
| b2_rag_cypher | To improve the conference experience next time, consider adjusting the scheduling and staffing around peak periods. High... | FAIL | REVIEW | Needs manual check |
| b2_rag_hybrid | Based on the community summaries, several improvements could enhance the conference experience next time. First, conside... | FAIL | FAIL | No answer generated |
| b3_aqr | To improve future conference events, consider the following recommendations:  1. **Staffing and Management**: The data i... | FAIL | REVIEW | Needs manual check |

### L5_q009_community_pattern_analysis
**Q:** Looking at the overall structure of activity on 2025-12-08, which groups of cameras and locations naturally cluster together based on their activity patterns? Describe 2-3 distinct activity clusters and what characterizes each one.
**Gold (rubric_coverage):** Gate cameras (MainEntrance, ParkingLot) form a cluster with entry/exit-dominated activity | Demo booth cameras (NVIDIA, Intel) form a cluster with similar crowd patterns | The keynote and expo areas s

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | On 2025-12-08, three distinct activity clusters were observed:  1. **Crowd Monitoring Areas**: Locations such as 'DemoBo... | PASS | PASS |  |
| b2_rag_cypher | On 2025-12-08, three distinct clusters of activity were observed based on event counts. The "DemoBooth_NVIDIA" location,... | FAIL | REVIEW | Needs manual check |
| b2_rag_hybrid | On December 8, 2025, the activity patterns across the observed locations form distinct clusters. The first cluster consi... | FAIL | REVIEW | Needs manual check |
| b3_aqr | On December 8, 2025, the activity at the 'DemoBooth_NVIDIA', 'ExpoFloor_MainAisle', and 'DemoBooth_Intel' locations were... | FAIL | REVIEW | Needs manual check |

### L5_q010_temporal_flow_narrative
**Q:** Describe the flow of people through the venue on 2025-12-08 — how did the crowd move from gates to the expo floor to the keynote hall to the food court throughout the day? Paint a picture of the temporal flow using the data.
**Gold (rubric_coverage):** Morning arrivals concentrated at Gate_MainEntrance and Gate_ParkingLot around 08-10 UTC | Crowd builds on the ExpoFloor and DemoBooths during mid-morning 10-12 UTC | Keynote sessions draw large crowds

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | On December 8, 2025, people began entering the venue steadily from midnight, with notable increases in entries at the Ga... | PASS | PASS |  |
| b2_rag_cypher | On December 8, 2025, the flow of people through the venue was consistent and peaked later in the day. Initially, crowd p... | PASS | PASS |  |
| b2_rag_hybrid | On December 8, 2025, the flow of people through the venue began with moderate activity at the gates, where the Main Entr... | FAIL | REVIEW | Needs manual check |
| b3_aqr | On December 8, 2025, the flow of people through the venue started at the gates, where significant foot traffic was obser... | FAIL | REVIEW | Needs manual check |

### L5_q011_venue_capacity_analysis
**Q:** Based on the crowd data, which areas of the venue seem overcrowded and which seem underutilized? Give me a capacity assessment with recommendations.
**Gold (rubric_coverage):** KeynoteHall_Stage has the highest crowd peaks (500) suggesting potential overcrowding | ExpoFloor_MainAisle has sustained high crowd levels throughout the day | DemoBooth_Intel has lower crowds than N

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The Keynote Hall Stage and Main Aisle on the Expo Floor seem overcrowded, with average head counts of 57.4 and 49.4, res... | FAIL | REVIEW | Needs manual check |
| b2_rag_cypher | The Keynote Hall Stage appears to be overcrowded, with a peak head count of 500 and an average head count of 57.40, sugg... | PASS | PASS |  |
| b2_rag_hybrid | The KeynoteHall_Stage appears overcrowded with a peak head count of 500, which indicates that it is a highly utilized ar... | PASS | PASS |  |
| b3_aqr | The venue's most overcrowded area appears to be the 'KeynoteHall_Stage', where the peak head count hits 500, indicating ... | PASS | PASS |  |

### L5_q012_incident_investigation
**Q:** Something happened at the keynote hall around 9 AM — the crowd surged massively. Investigate: how many people were there, where did they come from (which gates saw entry spikes before 9 AM), and where did they go afterwards?
**Gold (rubric_coverage):** KeynoteHall_Stage had a crowd peak around 09:00 with head_count around 450-500 | Gate_MainEntrance saw heavy person_entry traffic in the 08:00-09:00 window | KeynoteHall_DoorA had entry spikes aligned

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | At 9 AM, the keynote hall had a surge of up to 484 people present at '2025-12-08T09:01:33Z'. Before 9 AM, the Main Entra... | PASS | PASS |  |
| b2_rag_cypher | At 9 AM, there were 1,620,671 people in the Keynote Hall. Prior to 9 AM, 362 people entered through gates. After 9 AM, 2... | FAIL | REVIEW | Needs manual check |
| b2_rag_hybrid | At the keynote hall around 9 AM, a significant increase in crowd size was recorded, reaching a peak head count of 500 at... | PASS | PASS |  |
| b3_aqr | At around 9 AM in the keynote hall, there was a significant surge with a peak head count of 500, and an average head cou... | PASS | PASS |  |

### L5_q013_end_of_day_evacuation
**Q:** How did the end-of-day evacuation go? Describe the departure pattern from 17:00 onwards — which areas emptied first, how the gates handled the outflow, and whether the departure was orderly or had bottleneck moments.
**Gold (rubric_coverage):** Gate_MainEntrance saw heavy person_exit traffic in the 17:00-19:00 window | Gate_ParkingLot had car_exit spikes during the same evening window | Crowd levels at ExpoFloor and DemoBooths dropped as peo

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The end-of-day evacuation from 17:00 onwards saw the 'Gate_MainEntrance' handling the highest outflow, with a peak of 24... | PASS | PASS |  |
| b2_rag_cypher | The end-of-day evacuation from 17:00 onwards proceeded primarily through the main entrance and the parking lot gates. At... | PASS | PASS |  |
| b2_rag_hybrid | The end-of-day evacuation on December 8, 2025, began in earnest at 17:00, with significant activity at the Gate_MainEntr... | PASS | PASS |  |
| b3_aqr | The end-of-day evacuation on December 8, 2025, saw a substantial but orderly outflow of people primarily through the Gat... | PASS | PASS |  |

### L5_q014_venue_design_feedback
**Q:** If you were the venue designer looking at this data, what would you change about the layout? Which areas need more space, which need better flow, and where should food or rest areas be added?
**Gold (rubric_coverage):** KeynoteHall needs more capacity or overflow viewing | ExpoFloor has sustained high traffic — wider aisles or more space needed | FoodCourt peaks sharply at lunch — add satellite food stations | Gate a

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The "ExpoFloor_MainAisle" experiences the highest crowd with a total head count of 4,264,407 and sees its peak between 1... | FAIL | REVIEW | Needs manual check |
| b2_rag_cypher | The main entrance gate, with 2,951 entry/exit events, indicates a high traffic area that may benefit from increased spac... | FAIL | REVIEW | Needs manual check |
| b2_rag_hybrid | Reviewing the observed data, the KeynoteHall_Stage experiences the highest peak head count at 500, suggesting a need for... | PASS | PASS |  |
| b3_aqr | Based on the gathered data, the KeynoteHall_Stage has a significant peak head count of 500, indicating a need for more s... | PASS | PASS |  |

### L5_q015_vip_experience_report
**Q:** Write a report on the visitor experience at the demo booths today — were they well-attended, which one drew more interest, and how did the crowd flow between them and the rest of the venue?
**Gold (rubric_coverage):** NVIDIA booth drew larger crowds than Intel | Peak demo booth hours were during expo hours (10-12, 15-17) | Crowd at booths was lower than keynote and expo floor — booths are secondary attractions | Th

| Approach | Answer (truncated) | Auto | Manual | Notes |
|---|---|---|---|---|
| b1_sql | The visitor experience at the demo booths was well-attended, with the NVIDIA booth drawing more interest than the Intel ... | FAIL | REVIEW | Needs manual check |
| b2_rag_cypher | The demo booths at the venue were well-attended on December 8, 2025. "DemoBooth_NVIDIA" had a higher average head count ... | FAIL | REVIEW | Needs manual check |
| b2_rag_hybrid | Today at the demo booths, the NVIDIA booth was the standout attraction, drawing more interest than the Intel booth, as e... | PASS | PASS |  |
| b3_aqr | The visitor experience at the demo booths today was marked by substantial interest, particularly at the NVIDIA booth. Th... | PASS | PASS |  |
