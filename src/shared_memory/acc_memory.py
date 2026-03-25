"""Assetto Corsa Competizione shared memory reader.

ACC uses the same mapping names as AC but with extended structures.
Additional file: Local\\acpmf_crewChief
"""
from __future__ import annotations

import ctypes
import time
from typing import Optional

from .base_reader import BaseReader, open_shared_memory, close_shared_memory
from ..telemetry.data_models import TelemetryFrame


# ---------------------------------------------------------------------------
# ACC ctypes structures (extended over AC)
# ---------------------------------------------------------------------------

class ACCPhysics(ctypes.Structure):
    _fields_ = [
        ("packetId",                ctypes.c_int),
        ("gas",                     ctypes.c_float),
        ("brake",                   ctypes.c_float),
        ("fuel",                    ctypes.c_float),
        ("gear",                    ctypes.c_int),
        ("rpms",                    ctypes.c_int),
        ("steerAngle",              ctypes.c_float),
        ("speedKmh",                ctypes.c_float),
        ("velocity",                ctypes.c_float * 3),
        ("accG",                    ctypes.c_float * 3),
        ("wheelSlip",               ctypes.c_float * 4),
        ("wheelLoad",               ctypes.c_float * 4),
        ("wheelsPressure",          ctypes.c_float * 4),
        ("wheelAngularSpeed",       ctypes.c_float * 4),
        ("tyreWear",                ctypes.c_float * 4),
        ("tyreDirtyLevel",          ctypes.c_float * 4),
        ("tyreCoreTemperature",     ctypes.c_float * 4),
        ("camberRAD",               ctypes.c_float * 4),
        ("suspensionTravel",        ctypes.c_float * 4),
        ("drs",                     ctypes.c_float),
        ("tc",                      ctypes.c_float),
        ("heading",                 ctypes.c_float),
        ("pitch",                   ctypes.c_float),
        ("roll",                    ctypes.c_float),
        ("cgHeight",                ctypes.c_float),
        ("carDamage",               ctypes.c_float * 5),
        ("numberOfTyresOut",        ctypes.c_int),
        ("pitLimiterOn",            ctypes.c_int),
        ("abs",                     ctypes.c_float),
        ("kersCharge",              ctypes.c_float),
        ("kersInput",               ctypes.c_float),
        ("autoShifterOn",           ctypes.c_int),
        ("rideHeight",              ctypes.c_float * 2),
        ("turboBoost",              ctypes.c_float),
        ("ballast",                 ctypes.c_float),
        ("airDensity",              ctypes.c_float),
        ("airTemp",                 ctypes.c_float),
        ("roadTemp",                ctypes.c_float),
        ("localAngularVel",         ctypes.c_float * 3),
        ("finalFF",                 ctypes.c_float),
        ("performanceMeter",        ctypes.c_float),
        ("engineBrake",             ctypes.c_int),
        ("ersRecoveryLevel",        ctypes.c_int),
        ("ersPowerLevel",           ctypes.c_int),
        ("ersHeatCharging",         ctypes.c_int),
        ("ersIsCharging",           ctypes.c_int),
        ("kersCurrentKJ",           ctypes.c_float),
        ("drsAvailable",            ctypes.c_int),
        ("drsEnabled",              ctypes.c_int),
        ("brakeTemp",               ctypes.c_float * 4),
        ("clutch",                  ctypes.c_float),
        ("tyreTempI",               ctypes.c_float * 4),
        ("tyreTempM",               ctypes.c_float * 4),
        ("tyreTempO",               ctypes.c_float * 4),
        ("isAIControlled",          ctypes.c_int),
        ("tyreContactPoint",        (ctypes.c_float * 3) * 4),
        ("tyreContactNormal",       (ctypes.c_float * 3) * 4),
        ("tyreContactHeading",      (ctypes.c_float * 3) * 4),
        ("brakeBias",               ctypes.c_float),
        ("localVelocity",           ctypes.c_float * 3),
        # ACC additions
        ("waterTemp",               ctypes.c_float),
        ("brakePressure",           ctypes.c_float * 4),
        ("frontBrakeCompound",      ctypes.c_int),
        ("rearBrakeCompound",       ctypes.c_int),
        ("padLife",                 ctypes.c_float * 4),
        ("discLife",                ctypes.c_float * 4),
        ("ignitionOn",              ctypes.c_int),
        ("starterEngineOn",         ctypes.c_int),
        ("isEngineRunning",         ctypes.c_int),
        ("kersTorque",              ctypes.c_float),
        ("ersRecoveryLevel2",       ctypes.c_int),
        ("ersPowerLevel2",          ctypes.c_int),
    ]


class ACCGraphics(ctypes.Structure):
    _fields_ = [
        ("packetId",                ctypes.c_int),
        ("status",                  ctypes.c_int),
        ("session",                 ctypes.c_int),
        ("currentTime",             ctypes.c_wchar * 15),
        ("lastTime",                ctypes.c_wchar * 15),
        ("bestTime",                ctypes.c_wchar * 15),
        ("split",                   ctypes.c_wchar * 15),
        ("completedLaps",           ctypes.c_int),
        ("position",                ctypes.c_int),
        ("iCurrentTime",            ctypes.c_int),
        ("iLastTime",               ctypes.c_int),
        ("iBestTime",               ctypes.c_int),
        ("sessionTimeLeft",         ctypes.c_float),
        ("distanceTraveled",        ctypes.c_float),
        ("isInPit",                 ctypes.c_int),
        ("currentSectorIndex",      ctypes.c_int),
        ("lastSectorTime",          ctypes.c_int),
        ("numberOfLaps",            ctypes.c_int),
        ("tyreCompound",            ctypes.c_wchar * 33),
        ("replayTimeMultiplier",    ctypes.c_float),
        ("normalizedCarPosition",   ctypes.c_float),
        ("activeCars",              ctypes.c_int),
        ("carCoordinates",          (ctypes.c_float * 3) * 60),
        ("carID",                   ctypes.c_int * 60),
        ("playerCarID",             ctypes.c_int),
        ("penaltyTime",             ctypes.c_float),
        ("flag",                    ctypes.c_int),
        ("penalty",                 ctypes.c_int),
        ("idealLineOn",             ctypes.c_int),
        ("isInPitLane",             ctypes.c_int),
        ("surfaceGrip",             ctypes.c_float),
        ("mandatoryPitDone",        ctypes.c_int),
        ("windSpeed",               ctypes.c_float),
        ("windDirection",           ctypes.c_float),
        ("isSetupMenuVisible",      ctypes.c_int),
        ("mainDisplayIndex",        ctypes.c_int),
        ("secondaryDisplayIndex",   ctypes.c_int),
        ("tc",                      ctypes.c_int),
        ("tccut",                   ctypes.c_int),
        ("engineMap",               ctypes.c_int),
        ("abs",                     ctypes.c_int),
        ("fuelXLap",                ctypes.c_float),
        ("rainLights",              ctypes.c_int),
        ("flashingLights",          ctypes.c_int),
        ("lightsStage",             ctypes.c_int),
        ("exhaustTemperature",      ctypes.c_float),
        ("wiperLv",                 ctypes.c_int),
        ("driverStintTotalTimeLeft", ctypes.c_int),
        ("driverStintTimeLeft",     ctypes.c_int),
        ("rainTyres",               ctypes.c_int),
        ("sessionIndex",            ctypes.c_int),
        ("usedFuel",                ctypes.c_float),
        ("deltaLapTime",            ctypes.c_wchar * 15),
        ("iDeltaLapTime",           ctypes.c_int),
        ("estimatedLapTime",        ctypes.c_wchar * 15),
        ("iEstimatedLapTime",       ctypes.c_int),
        ("isDeltaPositive",         ctypes.c_int),
        ("iSplit",                  ctypes.c_int),
        ("isValidLap",              ctypes.c_int),
        ("fuelEstimatedLaps",       ctypes.c_float),
        ("trackStatus",             ctypes.c_wchar * 33),
        ("missingMandatoryPits",    ctypes.c_int),
        ("clock",                   ctypes.c_float),
        ("directionLightsLeft",     ctypes.c_int),
        ("directionLightsRight",    ctypes.c_int),
        ("globalYellow",            ctypes.c_int),
        ("globalYellow1",           ctypes.c_int),
        ("globalYellow2",           ctypes.c_int),
        ("globalYellow3",           ctypes.c_int),
        ("globalWhite",             ctypes.c_int),
        ("globalGreen",             ctypes.c_int),
        ("globalChequered",         ctypes.c_int),
        ("globalRed",               ctypes.c_int),
        ("mfdTyreSet",              ctypes.c_int),
        ("mfdFuelToAdd",            ctypes.c_float),
        ("mfdTyrePressureLF",       ctypes.c_float),
        ("mfdTyrePressureRF",       ctypes.c_float),
        ("mfdTyrePressureLR",       ctypes.c_float),
        ("mfdTyrePressureRR",       ctypes.c_float),
        ("trackGripStatus",         ctypes.c_int),
        ("rainIntensity",           ctypes.c_int),
        ("rainIntensityIn10min",    ctypes.c_int),
        ("rainIntensityIn30min",    ctypes.c_int),
        ("currentTyreSet",          ctypes.c_int),
        ("strategyTyreSet",         ctypes.c_int),
        ("gapAhead",                ctypes.c_int),
        ("gapBehind",               ctypes.c_int),
        # ACC-specific additions
        ("penaltyType",             ctypes.c_int),
        ("aidFuelRate",             ctypes.c_int),
        ("aidTireRate",             ctypes.c_int),
        ("aidMechanicalDamage",     ctypes.c_int),
        ("aidAllowTyreBlankets",    ctypes.c_int),
        ("aidStability",            ctypes.c_int),
        ("aidAutoclutch",           ctypes.c_int),
        ("aidAutoBlip",             ctypes.c_int),
        ("yellowFlagSectors",       ctypes.c_int * 3),
    ]


class ACCStatic(ctypes.Structure):
    _fields_ = [
        ("smVersion",               ctypes.c_wchar * 15),
        ("acVersion",               ctypes.c_wchar * 15),
        ("numberOfSessions",        ctypes.c_int),
        ("numCars",                 ctypes.c_int),
        ("carModel",                ctypes.c_wchar * 33),
        ("track",                   ctypes.c_wchar * 33),
        ("playerName",              ctypes.c_wchar * 33),
        ("playerSurname",           ctypes.c_wchar * 33),
        ("playerNick",              ctypes.c_wchar * 33),
        ("sectorCount",             ctypes.c_int),
        ("maxTorque",               ctypes.c_float),
        ("maxPower",                ctypes.c_float),
        ("maxRpm",                  ctypes.c_int),
        ("maxFuel",                 ctypes.c_float),
        ("suspensionMaxTravel",     ctypes.c_float * 4),
        ("tyreRadius",              ctypes.c_float * 4),
        ("maxTurboBoost",           ctypes.c_float),
        ("deprecated_1",            ctypes.c_float),
        ("deprecated_2",            ctypes.c_float),
        ("penaltiesEnabled",        ctypes.c_float),
        ("aidFuelRate",             ctypes.c_float),
        ("aidTireRate",             ctypes.c_float),
        ("aidMechanicalDamage",     ctypes.c_float),
        ("aidAllowTyreBlankets",    ctypes.c_float),
        ("aidStability",            ctypes.c_float),
        ("aidAutoclutch",           ctypes.c_float),
        ("aidAutoBlip",             ctypes.c_float),
        ("hasDRS",                  ctypes.c_int),
        ("hasERS",                  ctypes.c_int),
        ("hasKERS",                 ctypes.c_int),
        ("kersMaxJ",                ctypes.c_float),
        ("engineBrakeSettingsCount", ctypes.c_int),
        ("ersPowerControllerCount", ctypes.c_int),
        ("trackSPlineLength",       ctypes.c_float),
        ("trackConfiguration",      ctypes.c_wchar * 33),
        ("ersMaxJ",                 ctypes.c_float),
        ("isTimedRace",             ctypes.c_int),
        ("hasExtraLap",             ctypes.c_int),
        ("carSkin",                 ctypes.c_wchar * 33),
        ("reversedGridPositions",   ctypes.c_int),
        ("PitWindowStart",          ctypes.c_int),
        ("PitWindowEnd",            ctypes.c_int),
        ("isOnline",                ctypes.c_int),
        ("dryTyresName",            ctypes.c_wchar * 33),
        ("wetTyresName",            ctypes.c_wchar * 33),
    ]


class ACCReader(BaseReader):
    SIM_NAME = "Assetto Corsa Competizione"

    _PHYS_NAME   = "Local\\acpmf_physics"
    _GFX_NAME    = "Local\\acpmf_graphics"
    _STATIC_NAME = "Local\\acpmf_static"

    def __init__(self, poll_hz: int = 60):
        super().__init__(poll_hz)
        self._phys_handle   = None
        self._phys_ptr      = None
        self._gfx_handle    = None
        self._gfx_ptr       = None
        self._static_handle = None
        self._static_ptr    = None
        self._phys_buf   = ACCPhysics()
        self._gfx_buf    = ACCGraphics()
        self._static_buf = ACCStatic()
        self._is_acc     = False  # differentiates from AC after first read

    def _open(self) -> bool:
        self._phys_handle, self._phys_ptr     = open_shared_memory(self._PHYS_NAME)
        self._gfx_handle,  self._gfx_ptr      = open_shared_memory(self._GFX_NAME)
        self._static_handle, self._static_ptr = open_shared_memory(self._STATIC_NAME)
        return self._phys_ptr is not None

    def _close(self) -> None:
        close_shared_memory(self._phys_handle, self._phys_ptr)
        close_shared_memory(self._gfx_handle, self._gfx_ptr)
        close_shared_memory(self._static_handle, self._static_ptr)
        self._phys_handle = self._phys_ptr = None
        self._gfx_handle  = self._gfx_ptr  = None
        self._static_handle = self._static_ptr = None

    def _read_struct(self, ptr: int, buf: ctypes.Structure) -> None:
        ctypes.memmove(ctypes.addressof(buf), ptr, ctypes.sizeof(buf))

    def read_frame(self) -> Optional[TelemetryFrame]:
        if self._phys_ptr is None:
            if not self._open():
                return None

        try:
            self._read_struct(self._phys_ptr, self._phys_buf)
            if self._gfx_ptr:
                self._read_struct(self._gfx_ptr, self._gfx_buf)
            if self._static_ptr:
                self._read_struct(self._static_ptr, self._static_buf)
        except Exception:
            self._close()
            return None

        p = self._phys_buf
        g = self._gfx_buf
        s = self._static_buf

        if g.status == 0:
            return None

        # Find player world position from carCoordinates
        pid = g.playerCarID
        pos_x, pos_z = 0.0, 0.0
        for _i in range(min(g.activeCars, 60)):
            if g.carID[_i] == pid:
                pos_x = float(g.carCoordinates[_i][0])
                pos_z = float(g.carCoordinates[_i][2])
                break

        return TelemetryFrame(
            sim=self.SIM_NAME,
            timestamp_ms=int(time.time() * 1000),
            throttle=p.gas,
            brake=p.brake,
            clutch=p.clutch,
            steering=p.steerAngle,
            speed_kmh=p.speedKmh,
            gear=p.gear - 1,  # ACC: 0=R,1=N,2=1st → normalize to -1=R,0=N,1=1st
            rpm=float(p.rpms),
            rpm_max=float(s.maxRpm) if s.maxRpm > 0 else 8000.0,
            g_lat=p.accG[0],
            g_lon=p.accG[2],
            g_vert=p.accG[1],
            lap_number=g.completedLaps,
            lap_time_ms=g.iCurrentTime,
            last_lap_ms=g.iLastTime,
            best_lap_ms=g.iBestTime,
            lap_progress=g.normalizedCarPosition,
            sector_index=g.currentSectorIndex,
            is_valid_lap=bool(g.isValidLap),
            tyre_temp=list(p.tyreCoreTemperature),
            tyre_temp_i=list(p.tyreTempI),
            tyre_temp_m=list(p.tyreTempM),
            tyre_temp_o=list(p.tyreTempO),
            tyre_pressure=list(p.wheelsPressure),
            tyre_wear=list(p.tyreWear),
            suspension_travel=list(p.suspensionTravel),
            fuel=p.fuel,
            is_in_pit=bool(g.isInPit),
            is_in_pit_lane=bool(g.isInPitLane),
            pit_limiter=bool(p.pitLimiterOn),
            tc_active=p.tc > 0,
            abs_active=p.abs > 0,
            drs_active=bool(p.drsEnabled),
            car_model=s.carModel,
            track=s.track,
            position=g.position,
            brake_temp=list(p.brakeTemp),
            ride_height_front=p.rideHeight[0],
            ride_height_rear=p.rideHeight[1],
            brake_bias=p.brakeBias,
            water_temp=p.waterTemp,
            tyre_compound=g.tyreCompound,
            session_time_left=g.sessionTimeLeft,
            gap_ahead_ms=g.gapAhead,
            gap_behind_ms=g.gapBehind,
            pos_x=pos_x,
            pos_z=pos_z,
        )
