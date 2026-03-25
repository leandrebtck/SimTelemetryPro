"""Le Mans Ultimate shared memory reader.

LMU is built on rFactor 2 and uses the rF2 Shared Memory Plugin.
Plugin creates mapped files prefixed with $rFactor2SMMP_.

Required: the rF2 / LMU shared memory plugin must be installed and enabled
in the game (usually auto-installed with LMU).

Key files:
  $rFactor2SMMP_TelemetryV2$  - vehicle physics (per physics tick)
  $rFactor2SMMP_ScoringV2$    - session / scoring info
  $rFactor2SMMP_ExtendedV2$   - extended plugin data
"""
from __future__ import annotations

import ctypes
import time
from typing import Optional

from .base_reader import BaseReader, open_shared_memory, close_shared_memory
from ..telemetry.data_models import TelemetryFrame

# ---------------------------------------------------------------------------
# rF2 / LMU shared memory structures
# ---------------------------------------------------------------------------

class rF2Vec3(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double), ("z", ctypes.c_double)]


class rF2Wheel(ctypes.Structure):
    _fields_ = [
        ("mSuspensionDeflection",   ctypes.c_double),
        ("mRideHeight",             ctypes.c_double),
        ("mSuspForce",              ctypes.c_double),
        ("mBrakeTemp",              ctypes.c_double),
        ("mBrakePressure",          ctypes.c_double),
        ("mRotation",               ctypes.c_double),
        ("mLateralPatchVel",        ctypes.c_double),
        ("mLongitudinalPatchVel",   ctypes.c_double),
        ("mLateralGroundVel",       ctypes.c_double),
        ("mLongitudinalGroundVel",  ctypes.c_double),
        ("mCamber",                 ctypes.c_double),
        ("mLateralForce",           ctypes.c_double),
        ("mLongitudinalForce",      ctypes.c_double),
        ("mTireLoad",               ctypes.c_double),
        ("mGripFract",              ctypes.c_double),
        ("mPressure",               ctypes.c_double),
        ("mTemperature",            ctypes.c_double * 3),  # inner, center, outer
        ("mWear",                   ctypes.c_double),
        ("mTerrainName",            ctypes.c_char * 16),
        ("mSurfaceType",            ctypes.c_ubyte),
        ("mFlat",                   ctypes.c_ubyte),
        ("mDetached",               ctypes.c_ubyte),
        ("mStaticUnbalanceMag",     ctypes.c_ubyte),
        ("mVerticalTireDeflection", ctypes.c_double),
        ("mWheelYLocation",         ctypes.c_double),
        ("mToe",                    ctypes.c_double),
        ("mTireCarcassTemperature", ctypes.c_double),
        ("mTireInnerLayerTemperature", ctypes.c_double * 3),
        ("mExpansion",              ctypes.c_ubyte * 24),
    ]


class rF2VehicleTelemetry(ctypes.Structure):
    _fields_ = [
        ("mID",                     ctypes.c_int),
        ("mDeltaTime",              ctypes.c_double),
        ("mElapsedTime",            ctypes.c_double),
        ("mLapNumber",              ctypes.c_int),
        ("mLapStartET",             ctypes.c_double),
        ("mVehicleName",            ctypes.c_char * 64),
        ("mTrackName",              ctypes.c_char * 64),
        ("mPos",                    rF2Vec3),
        ("mLocalVel",               rF2Vec3),
        ("mLocalAccel",             rF2Vec3),
        ("mOri",                    rF2Vec3 * 3),
        ("mLocalRot",               rF2Vec3),
        ("mLocalRotAccel",          rF2Vec3),
        ("mGear",                   ctypes.c_int),
        ("mEngineRPM",              ctypes.c_double),
        ("mEngineWaterTemp",        ctypes.c_double),
        ("mEngineOilTemp",          ctypes.c_double),
        ("mClutchRPM",              ctypes.c_double),
        ("mUnfilteredThrottle",     ctypes.c_double),
        ("mUnfilteredBrake",        ctypes.c_double),
        ("mUnfilteredSteering",     ctypes.c_double),
        ("mUnfilteredClutch",       ctypes.c_double),
        ("mFilteredThrottle",       ctypes.c_double),
        ("mFilteredBrake",          ctypes.c_double),
        ("mFilteredSteering",       ctypes.c_double),
        ("mFilteredClutch",         ctypes.c_double),
        ("mSteeringShaftTorque",    ctypes.c_double),
        ("mFront3rdDeflection",     ctypes.c_double),
        ("mRear3rdDeflection",      ctypes.c_double),
        ("mFrontWingHeight",        ctypes.c_double),
        ("mFrontRideHeight",        ctypes.c_double),
        ("mRearRideHeight",         ctypes.c_double),
        ("mDrag",                   ctypes.c_double),
        ("mFrontDownforce",         ctypes.c_double),
        ("mRearDownforce",          ctypes.c_double),
        ("mFuel",                   ctypes.c_double),
        ("mEngineMaxRPM",           ctypes.c_double),
        ("mScheduledStops",         ctypes.c_ubyte),
        ("mOverheating",            ctypes.c_ubyte),
        ("mDetached",               ctypes.c_ubyte),
        ("mHeadlights",             ctypes.c_ubyte),
        ("mDentSeverity",           ctypes.c_ubyte * 8),
        ("mLastImpactET",           ctypes.c_double),
        ("mLastImpactMagnitude",    ctypes.c_double),
        ("mLastImpactPos",          rF2Vec3),
        ("mEngineTorque",           ctypes.c_double),
        ("mCurrentSector",          ctypes.c_int),
        ("mSpeedLimiter",           ctypes.c_ubyte),
        ("mMaxGears",               ctypes.c_ubyte),
        ("mFrontTireCompoundIndex", ctypes.c_ubyte),
        ("mRearTireCompoundIndex",  ctypes.c_ubyte),
        ("mFuelCapacity",           ctypes.c_double),
        ("mFrontFlapActivated",     ctypes.c_ubyte),
        ("mRearFlapActivated",      ctypes.c_ubyte),
        ("mRearFlapLegalStatus",    ctypes.c_ubyte),
        ("mIgnitionStarter",        ctypes.c_ubyte),
        ("mFrontTireCompoundName",  ctypes.c_char * 18),
        ("mRearTireCompoundName",   ctypes.c_char * 18),
        ("mSpeedLimiterAvailable",  ctypes.c_ubyte),
        ("mAntiStallActivated",     ctypes.c_ubyte),
        ("mUnused",                 ctypes.c_ubyte * 2),
        ("mVisualSteeringWheelRange", ctypes.c_float),
        ("mRearBrakeBias",          ctypes.c_double),
        ("mTurboBoostPressure",     ctypes.c_double),
        ("mPhysicsToGraphicsOffset", ctypes.c_float * 3),
        ("mPhysicalSteeringWheelRange", ctypes.c_float),
        ("mExpansion",              ctypes.c_ubyte * 152),
        # Wheels: LF, RF, LR, RR
        ("mWheel",                  rF2Wheel * 4),
    ]


# Scoring info per vehicle
class rF2VehicleScoring(ctypes.Structure):
    _fields_ = [
        ("mID",                     ctypes.c_int),
        ("mDriverName",             ctypes.c_char * 32),
        ("mVehicleName",            ctypes.c_char * 64),
        ("mTotalLaps",              ctypes.c_short),
        ("mSector",                 ctypes.c_byte),
        ("mFinishStatus",           ctypes.c_byte),
        ("mLapDist",                ctypes.c_double),
        ("mPathLateral",            ctypes.c_double),
        ("mTrackEdge",              ctypes.c_double),
        ("mBestSector1",            ctypes.c_double),
        ("mBestSector2",            ctypes.c_double),
        ("mBestLapTime",            ctypes.c_double),
        ("mLastSector1",            ctypes.c_double),
        ("mLastSector2",            ctypes.c_double),
        ("mLastLapTime",            ctypes.c_double),
        ("mCurSector1",             ctypes.c_double),
        ("mCurSector2",             ctypes.c_double),
        ("mNumPitstops",            ctypes.c_short),
        ("mNumPenalties",           ctypes.c_short),
        ("mIsPlayer",               ctypes.c_ubyte),
        ("mControl",                ctypes.c_byte),
        ("mInPits",                 ctypes.c_ubyte),
        ("mPlace",                  ctypes.c_ubyte),
        ("mVehicleClass",           ctypes.c_char * 32),
        ("mTimeBehindNext",         ctypes.c_double),
        ("mLapsBehindNext",         ctypes.c_int),
        ("mTimeBehindLeader",       ctypes.c_double),
        ("mLapsBehindLeader",       ctypes.c_int),
        ("mLapStartET",             ctypes.c_double),
        ("mPos",                    rF2Vec3),
        ("mLocalVel",               rF2Vec3),
        ("mLocalAccel",             rF2Vec3),
        ("mOri",                    rF2Vec3 * 3),
        ("mLocalRot",               rF2Vec3),
        ("mLocalRotAccel",          rF2Vec3),
        ("mHeadlights",             ctypes.c_ubyte),
        ("mPitState",               ctypes.c_ubyte),
        ("mServerScored",           ctypes.c_ubyte),
        ("mIndividualPhase",        ctypes.c_ubyte),
        ("mQualification",          ctypes.c_int),
        ("mTimeIntoLap",            ctypes.c_double),
        ("mEstimatedLapTime",       ctypes.c_double),
        ("mPitGroup",               ctypes.c_char * 24),
        ("mFlag",                   ctypes.c_ubyte),
        ("mUnderYellow",            ctypes.c_ubyte),
        ("mCountLapFlag",           ctypes.c_ubyte),
        ("mInGarageStall",          ctypes.c_ubyte),
        ("mUpgradePack",            ctypes.c_char * 16),
        ("mPitLapDist",             ctypes.c_float),
        ("mBestLapSector1",         ctypes.c_float),
        ("mBestLapSector2",         ctypes.c_float),
        ("mExpansion",              ctypes.c_ubyte * 48),
    ]


_MAX_VEHICLES = 128


class rF2ScoringInfo(ctypes.Structure):
    _fields_ = [
        ("mTrackName",              ctypes.c_char * 64),
        ("mSession",                ctypes.c_int),
        ("mCurrentET",              ctypes.c_double),
        ("mEndET",                  ctypes.c_double),
        ("mMaxLaps",                ctypes.c_int),
        ("mLapDist",                ctypes.c_double),
        ("mResultsStream",          ctypes.c_char * 1),
        ("mNumVehicles",            ctypes.c_int),
        ("mGamePhase",              ctypes.c_ubyte),
        ("mYellowFlagState",        ctypes.c_byte),
        ("mSectorFlag",             ctypes.c_byte * 3),
        ("mStartLight",             ctypes.c_ubyte),
        ("mNumRedLights",           ctypes.c_ubyte),
        ("mInRealtime",             ctypes.c_ubyte),
        ("mPlayerName",             ctypes.c_char * 32),
        ("mPlrFileName",            ctypes.c_char * 64),
        ("mDarkCloud",              ctypes.c_double),
        ("mRaining",                ctypes.c_double),
        ("mAmbientTemp",            ctypes.c_double),
        ("mTrackTemp",              ctypes.c_double),
        ("mWind",                   rF2Vec3),
        ("mMinPathWetness",         ctypes.c_double),
        ("mMaxPathWetness",         ctypes.c_double),
        ("mGameMode",               ctypes.c_ubyte),
        ("mIsPasswordProtected",    ctypes.c_ubyte),
        ("mServerPort",             ctypes.c_ushort),
        ("mServerPublicIP",         ctypes.c_uint),
        ("mMaxPlayers",             ctypes.c_int),
        ("mServerName",             ctypes.c_char * 32),
        ("mStartET",                ctypes.c_float),
        ("mAvgPathWetness",         ctypes.c_double),
        ("mExpansion",              ctypes.c_ubyte * 200),
        ("mVehicles",               rF2VehicleScoring * _MAX_VEHICLES),
    ]


class rF2Telemetry(ctypes.Structure):
    _fields_ = [
        ("mVersionUpdateBegin",     ctypes.c_uint),
        ("mVersionUpdateEnd",       ctypes.c_uint),
        ("mBytesUpdatedHint",       ctypes.c_int),
        ("mNumVehicles",            ctypes.c_int),
        ("mVehicles",               rF2VehicleTelemetry * _MAX_VEHICLES),
    ]


class rF2Scoring(ctypes.Structure):
    _fields_ = [
        ("mVersionUpdateBegin",     ctypes.c_uint),
        ("mVersionUpdateEnd",       ctypes.c_uint),
        ("mBytesUpdatedHint",       ctypes.c_int),
        ("mScoringInfo",            rF2ScoringInfo),
    ]


# ---------------------------------------------------------------------------
# Reader
# ---------------------------------------------------------------------------

class LMUReader(BaseReader):
    SIM_NAME = "Le Mans Ultimate"

    _TELE_NAME   = "$rFactor2SMMP_TelemetryV2$"
    _SCORE_NAME  = "$rFactor2SMMP_ScoringV2$"

    def __init__(self, poll_hz: int = 60):
        super().__init__(poll_hz)
        self._tele_handle  = None
        self._tele_ptr     = None
        self._score_handle = None
        self._score_ptr    = None
        self._tele_buf     = rF2Telemetry()
        self._score_buf    = rF2Scoring()
        self._best_lap_s   = 0.0

    def _open(self) -> bool:
        self._tele_handle,  self._tele_ptr  = open_shared_memory(self._TELE_NAME)
        self._score_handle, self._score_ptr = open_shared_memory(self._SCORE_NAME)
        return self._tele_ptr is not None

    def _close(self) -> None:
        close_shared_memory(self._tele_handle, self._tele_ptr)
        close_shared_memory(self._score_handle, self._score_ptr)
        self._tele_handle  = self._tele_ptr  = None
        self._score_handle = self._score_ptr = None

    def _read_struct(self, ptr: int, buf: ctypes.Structure) -> None:
        ctypes.memmove(ctypes.addressof(buf), ptr, ctypes.sizeof(buf))

    def _find_player(self) -> Optional[tuple[rF2VehicleTelemetry, rF2VehicleScoring]]:
        t = self._tele_buf
        s = self._score_buf.mScoringInfo
        if t.mNumVehicles <= 0:
            return None
        for i in range(min(t.mNumVehicles, _MAX_VEHICLES)):
            scoring_idx = -1
            for j in range(min(s.mNumVehicles, _MAX_VEHICLES)):
                if s.mVehicles[j].mID == t.mVehicles[i].mID and s.mVehicles[j].mIsPlayer:
                    scoring_idx = j
                    break
            if scoring_idx >= 0:
                return t.mVehicles[i], s.mVehicles[scoring_idx]
        # Fallback: first vehicle
        return t.mVehicles[0], s.mVehicles[0] if s.mNumVehicles > 0 else None

    def read_frame(self) -> Optional[TelemetryFrame]:
        if self._tele_ptr is None:
            if not self._open():
                return None

        try:
            self._read_struct(self._tele_ptr, self._tele_buf)
            if self._score_ptr:
                self._read_struct(self._score_ptr, self._score_buf)
        except Exception:
            self._close()
            return None

        if self._tele_buf.mNumVehicles <= 0:
            return None

        result = self._find_player()
        if result is None:
            return None
        vt, vs = result

        # Speed from local velocity
        lv = vt.mLocalVel
        speed_ms = (lv.x**2 + lv.y**2 + lv.z**2) ** 0.5
        speed_kmh = speed_ms * 3.6

        scoring = self._score_buf.mScoringInfo

        # Best lap tracking
        if vs is not None and vs.mBestLapTime > 0:
            self._best_lap_s = vs.mBestLapTime

        # Tyre temps (LF, RF, LR, RR) - use center temperature
        tyre_temp = [vt.mWheel[i].mTemperature[1] for i in range(4)]
        tyre_temp_i = [vt.mWheel[i].mTemperature[0] for i in range(4)]
        tyre_temp_o = [vt.mWheel[i].mTemperature[2] for i in range(4)]
        tyre_pressure = [vt.mWheel[i].mPressure * 0.001 for i in range(4)]  # Pa -> kPa
        tyre_wear = [1.0 - vt.mWheel[i].mWear for i in range(4)]
        suspension_travel = [vt.mWheel[i].mSuspensionDeflection for i in range(4)]
        brake_temp = [vt.mWheel[i].mBrakeTemp for i in range(4)]

        lap_time_ms = int(vs.mTimeIntoLap * 1000) if vs else 0
        last_lap_ms = int(vs.mLastLapTime * 1000) if vs else 0
        best_lap_ms = int(self._best_lap_s * 1000)
        lap_number  = int(vs.mTotalLaps) if vs else 0
        position    = int(vs.mPlace)     if vs else 0
        in_pits     = bool(vs.mInPits)   if vs else False
        lap_progress_dist = vs.mLapDist  if vs else 0.0
        track_len         = scoring.mLapDist if scoring.mLapDist > 0 else 1.0
        lap_progress      = lap_progress_dist / track_len

        return TelemetryFrame(
            sim=self.SIM_NAME,
            timestamp_ms=int(time.time() * 1000),
            throttle=float(vt.mFilteredThrottle),
            brake=float(vt.mFilteredBrake),
            clutch=float(vt.mFilteredClutch),
            steering=float(vt.mFilteredSteering),
            speed_kmh=speed_kmh,
            gear=int(vt.mGear),
            rpm=float(vt.mEngineRPM),
            rpm_max=float(vt.mEngineMaxRPM) if vt.mEngineMaxRPM > 0 else 8000.0,
            g_lat=float(vt.mLocalAccel.x) / 9.81,
            g_lon=float(vt.mLocalAccel.z) / 9.81,
            g_vert=float(vt.mLocalAccel.y) / 9.81,
            lap_number=lap_number,
            lap_time_ms=lap_time_ms,
            last_lap_ms=last_lap_ms,
            best_lap_ms=best_lap_ms,
            lap_progress=lap_progress,
            sector_index=int(vt.mCurrentSector),
            is_valid_lap=True,
            tyre_temp=tyre_temp,
            tyre_temp_i=tyre_temp_i,
            tyre_temp_m=tyre_temp,
            tyre_temp_o=tyre_temp_o,
            tyre_pressure=tyre_pressure,
            tyre_wear=tyre_wear,
            suspension_travel=suspension_travel,
            fuel=float(vt.mFuel),
            is_in_pit=in_pits,
            is_in_pit_lane=in_pits,
            pit_limiter=bool(vt.mSpeedLimiter),
            tc_active=False,
            abs_active=False,
            drs_active=bool(vt.mRearFlapActivated),
            car_model=vt.mVehicleName.decode("utf-8", errors="replace"),
            track=scoring.mTrackName.decode("utf-8", errors="replace"),
            position=position,
            brake_temp=brake_temp,
            ride_height_front=float(vt.mFrontRideHeight),
            ride_height_rear=float(vt.mRearRideHeight),
            brake_bias=float(vt.mRearBrakeBias),
            water_temp=float(vt.mEngineWaterTemp),
            pos_x=float(vt.mPos.x),
            pos_z=float(vt.mPos.z),
        )
