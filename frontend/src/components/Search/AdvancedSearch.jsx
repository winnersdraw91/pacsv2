import { useState } from "react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Card, CardContent } from "../ui/card";
import { Search, X, Filter } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../ui/dialog";

export default function AdvancedSearch({ onSearch, onReset }) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [searchParams, setSearchParams] = useState({
    patient_name: "",
    study_id: "",
    modality: "",
    status: "",
    date_from: "",
    date_to: "",
    patient_age_min: "",
    patient_age_max: "",
    patient_gender: "",
    include_drafts: false
  });

  const handleQuickSearch = (e) => {
    e.preventDefault();
    if (onSearch) {
      onSearch(searchParams);
    }
  };

  const handleAdvancedSearch = () => {
    if (onSearch) {
      onSearch(searchParams);
    }
    setShowAdvanced(false);
  };

  const handleReset = () => {
    const resetParams = {
      patient_name: "",
      study_id: "",
      modality: "",
      status: "",
      date_from: "",
      date_to: "",
      patient_age_min: "",
      patient_age_max: "",
      patient_gender: "",
      include_drafts: false
    };
    setSearchParams(resetParams);
    if (onReset) {
      onReset();
    }
  };

  const updateParam = (key, value) => {
    setSearchParams(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className="space-y-4">
      {/* Quick Search Bar */}
      <div className="flex gap-2">
        <form onSubmit={handleQuickSearch} className="flex-1 flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" />
            <Input
              type="text"
              placeholder="Search by patient name or study ID..."
              value={searchParams.patient_name || searchParams.study_id}
              onChange={(e) => {
                updateParam("patient_name", e.target.value);
                updateParam("study_id", e.target.value);
              }}
              className="pl-10 h-11"
              data-testid="quick-search-input"
            />
          </div>
          <Button type="submit" className="bg-teal-600 hover:bg-teal-700 h-11" data-testid="quick-search-button">
            <Search className="w-5 h-5 mr-2" />
            Search
          </Button>
        </form>

        <Dialog open={showAdvanced} onOpenChange={setShowAdvanced}>
          <DialogTrigger asChild>
            <Button variant="outline" className="border-slate-300 h-11" data-testid="advanced-filter-button">
              <Filter className="w-5 h-5 mr-2" />
              Filters
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Advanced Search Filters</DialogTitle>
            </DialogHeader>
            
            <div className="space-y-4">
              {/* Patient Information */}
              <Card>
                <CardContent className="pt-6">
                  <h3 className="font-semibold mb-4 text-slate-800">Patient Information</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Patient Name</Label>
                      <Input
                        value={searchParams.patient_name}
                        onChange={(e) => updateParam("patient_name", e.target.value)}
                        placeholder="Enter patient name"
                      />
                    </div>
                    <div>
                      <Label>Study ID</Label>
                      <Input
                        value={searchParams.study_id}
                        onChange={(e) => updateParam("study_id", e.target.value)}
                        placeholder="8-digit study ID"
                      />
                    </div>
                    <div>
                      <Label>Gender</Label>
                      <Select value={searchParams.patient_gender || "all"} onValueChange={(val) => updateParam("patient_gender", val === "all" ? "" : val)}>
                        <SelectTrigger>
                          <SelectValue placeholder="All Genders" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Genders</SelectItem>
                          <SelectItem value="Male">Male</SelectItem>
                          <SelectItem value="Female">Female</SelectItem>
                          <SelectItem value="Other">Other</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label>Age Range</Label>
                      <div className="flex gap-2">
                        <Input
                          type="number"
                          value={searchParams.patient_age_min}
                          onChange={(e) => updateParam("patient_age_min", parseInt(e.target.value) || "")}
                          placeholder="Min"
                        />
                        <Input
                          type="number"
                          value={searchParams.patient_age_max}
                          onChange={(e) => updateParam("patient_age_max", parseInt(e.target.value) || "")}
                          placeholder="Max"
                        />
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Study Details */}
              <Card>
                <CardContent className="pt-6">
                  <h3 className="font-semibold mb-4 text-slate-800">Study Details</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Modality</Label>
                      <Select value={searchParams.modality} onValueChange={(val) => updateParam("modality", val)}>
                        <SelectTrigger>
                          <SelectValue placeholder="All Modalities" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="">All Modalities</SelectItem>
                          <SelectItem value="CT">CT Scan</SelectItem>
                          <SelectItem value="MRI">MRI</SelectItem>
                          <SelectItem value="X-ray">X-ray</SelectItem>
                          <SelectItem value="Ultrasound">Ultrasound</SelectItem>
                          <SelectItem value="PET">PET Scan</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label>Status</Label>
                      <Select value={searchParams.status} onValueChange={(val) => updateParam("status", val)}>
                        <SelectTrigger>
                          <SelectValue placeholder="All Statuses" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="">All Statuses</SelectItem>
                          <SelectItem value="pending">Pending</SelectItem>
                          <SelectItem value="assigned">Assigned</SelectItem>
                          <SelectItem value="completed">Completed</SelectItem>
                          <SelectItem value="draft">Draft</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Date Range */}
              <Card>
                <CardContent className="pt-6">
                  <h3 className="font-semibold mb-4 text-slate-800">Date Range</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>From Date</Label>
                      <Input
                        type="date"
                        value={searchParams.date_from}
                        onChange={(e) => updateParam("date_from", e.target.value)}
                      />
                    </div>
                    <div>
                      <Label>To Date</Label>
                      <Input
                        type="date"
                        value={searchParams.date_to}
                        onChange={(e) => updateParam("date_to", e.target.value)}
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Options */}
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="include_drafts"
                      checked={searchParams.include_drafts}
                      onChange={(e) => updateParam("include_drafts", e.target.checked)}
                      className="w-4 h-4 text-teal-600 rounded focus:ring-teal-500"
                    />
                    <Label htmlFor="include_drafts" className="cursor-pointer">
                      Include Draft Studies
                    </Label>
                  </div>
                </CardContent>
              </Card>

              {/* Action Buttons */}
              <div className="flex gap-3 pt-4">
                <Button
                  variant="outline"
                  onClick={handleReset}
                  className="flex-1"
                  data-testid="reset-filters-button"
                >
                  <X className="w-4 h-4 mr-2" />
                  Reset Filters
                </Button>
                <Button
                  onClick={handleAdvancedSearch}
                  className="flex-1 bg-teal-600 hover:bg-teal-700"
                  data-testid="apply-filters-button"
                >
                  <Search className="w-4 h-4 mr-2" />
                  Apply Filters
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>

        {(searchParams.patient_name || searchParams.study_id || searchParams.modality || searchParams.status) && (
          <Button
            variant="outline"
            onClick={handleReset}
            className="border-slate-300 h-11"
            data-testid="clear-search-button"
          >
            <X className="w-5 h-5" />
          </Button>
        )}
      </div>

      {/* Active Filters Display */}
      {(searchParams.modality || searchParams.status || searchParams.date_from || searchParams.patient_gender) && (
        <div className="flex flex-wrap gap-2">
          {searchParams.modality && (
            <span className="px-3 py-1 bg-teal-100 text-teal-800 rounded-full text-sm font-medium">
              Modality: {searchParams.modality}
            </span>
          )}
          {searchParams.status && (
            <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
              Status: {searchParams.status}
            </span>
          )}
          {searchParams.patient_gender && (
            <span className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm font-medium">
              Gender: {searchParams.patient_gender}
            </span>
          )}
          {searchParams.date_from && (
            <span className="px-3 py-1 bg-orange-100 text-orange-800 rounded-full text-sm font-medium">
              From: {searchParams.date_from}
            </span>
          )}
          {searchParams.date_to && (
            <span className="px-3 py-1 bg-orange-100 text-orange-800 rounded-full text-sm font-medium">
              To: {searchParams.date_to}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
