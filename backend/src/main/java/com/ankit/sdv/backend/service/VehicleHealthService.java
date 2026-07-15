package com.ankit.sdv.backend.service;

import com.ankit.sdv.backend.dto.VehicleHealthResponse;

public interface VehicleHealthService {

    VehicleHealthResponse getCurrentHealth(String vehicleId);
}