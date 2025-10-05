import { useState, useEffect, useContext } from "react";
import { Routes, Route, Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { AuthContext } from "../../App";
import { Button } from "../ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card";
import { Input } from "../ui/input";
import { Building2, Users, FileText, Activity, LogOut, Plus, UserCheck, DollarSign } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../ui/dialog";
import { Label } from "../ui/label";
import AdvancedSearch from "../Search/AdvancedSearch";

const Sidebar = ({ logout }) => {
  return (
    <div className="w-64 bg-gradient-to-br from-slate-800 to-slate-900 text-white min-h-screen p-6 flex flex-col">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-lg bg-teal-500 flex items-center justify-center">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <h2 className="font-bold text-lg">PACS System</h2>
            <p className="text-xs text-slate-400">Admin Portal</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-2">
        <Link to="/admin" data-testid="admin-dashboard-link">
          <div className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-white/10 transition-colors">
            <Activity className="w-5 h-5" />
            <span className="font-medium">Dashboard</span>
          </div>
        </Link>
        <Link to="/admin/centres" data-testid="centres-link">
          <div className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-white/10 transition-colors">
            <Building2 className="w-5 h-5" />
            <span className="font-medium">Centres</span>
          </div>
        </Link>
        <Link to="/admin/radiologists" data-testid="radiologists-link">
          <div className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-white/10 transition-colors">
            <UserCheck className="w-5 h-5" />
            <span className="font-medium">Radiologists</span>
          </div>
        </Link>
        <Link to="/admin/studies" data-testid="studies-link">
          <div className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-white/10 transition-colors">
            <FileText className="w-5 h-5" />
            <span className="font-medium">All Studies</span>
          </div>
        </Link>
        <Link to="/admin/billing" data-testid="billing-link">
          <div className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-white/10 transition-colors">
            <DollarSign className="w-5 h-5" />
            <span className="font-medium">Billing</span>
          </div>
        </Link>
      </nav>

      <Button
        onClick={logout}
        variant="outline"
        className="w-full justify-start gap-3 border-slate-700 text-white hover:bg-white/10"
        data-testid="logout-button"
      >
        <LogOut className="w-5 h-5" />
        Logout
      </Button>
    </div>
  );
};

const DashboardHome = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get("/dashboard/stats");
      setStats(response.data);
    } catch (error) {
      console.error("Failed to fetch stats:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center"><div className="spinner mx-auto"></div></div>;
  }

  return (
    <div className="space-y-6" data-testid="admin-dashboard-home">
      <div>
        <h1 className="text-3xl font-bold text-slate-800 mb-2">Dashboard Overview</h1>
        <p className="text-slate-600">System-wide statistics and metrics</p>
      </div>

      <div className="dashboard-grid">
        <Card className="border-l-4 border-l-teal-500 shadow-md card-hover">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-600">Total Centres</p>
                <h3 className="text-3xl font-bold text-slate-800 mt-1">{stats?.total_centres || 0}</h3>
              </div>
              <div className="w-14 h-14 rounded-full bg-teal-100 flex items-center justify-center">
                <Building2 className="w-7 h-7 text-teal-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-cyan-500 shadow-md card-hover">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-600">Total Studies</p>
                <h3 className="text-3xl font-bold text-slate-800 mt-1">{stats?.total_studies || 0}</h3>
              </div>
              <div className="w-14 h-14 rounded-full bg-cyan-100 flex items-center justify-center">
                <FileText className="w-7 h-7 text-cyan-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-blue-500 shadow-md card-hover">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-600">Radiologists</p>
                <h3 className="text-3xl font-bold text-slate-800 mt-1">{stats?.total_radiologists || 0}</h3>
              </div>
              <div className="w-14 h-14 rounded-full bg-blue-100 flex items-center justify-center">
                <Users className="w-7 h-7 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-amber-500 shadow-md card-hover">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-600">Pending Studies</p>
                <h3 className="text-3xl font-bold text-slate-800 mt-1">{stats?.pending_studies || 0}</h3>
              </div>
              <div className="w-14 h-14 rounded-full bg-amber-100 flex items-center justify-center">
                <Activity className="w-7 h-7 text-amber-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

const CentresManagement = () => {
  const [centres, setCentres] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [formData, setFormData] = useState({ name: "", address: "", phone: "", email: "" });

  useEffect(() => {
    fetchCentres();
  }, []);

  const fetchCentres = async () => {
    try {
      const response = await axios.get("/centres");
      setCentres(response.data);
    } catch (error) {
      console.error("Failed to fetch centres:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await axios.post("/centres", formData);
      setShowCreateDialog(false);
      setFormData({ name: "", address: "", phone: "", email: "" });
      fetchCentres();
    } catch (error) {
      console.error("Failed to create centre:", error);
      alert("Failed to create centre");
    }
  };

  if (loading) {
    return <div className="p-8 text-center"><div className="spinner mx-auto"></div></div>;
  }

  return (
    <div className="space-y-6" data-testid="centres-management">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-800 mb-2">Diagnostic Centres</h1>
          <p className="text-slate-600">Manage all diagnostic centres</p>
        </div>
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogTrigger asChild>
            <Button className="bg-teal-600 hover:bg-teal-700" data-testid="create-centre-button">
              <Plus className="w-5 h-5 mr-2" />
              Add Centre
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Centre</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <Label>Centre Name</Label>
                <Input value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} required />
              </div>
              <div>
                <Label>Address</Label>
                <Input value={formData.address} onChange={(e) => setFormData({ ...formData, address: e.target.value })} required />
              </div>
              <div>
                <Label>Phone</Label>
                <Input value={formData.phone} onChange={(e) => setFormData({ ...formData, phone: e.target.value })} required />
              </div>
              <div>
                <Label>Email</Label>
                <Input type="email" value={formData.email} onChange={(e) => setFormData({ ...formData, email: e.target.value })} required />
              </div>
              <Button type="submit" className="w-full bg-teal-600 hover:bg-teal-700">Create Centre</Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Centre Name</th>
                  <th>Address</th>
                  <th>Phone</th>
                  <th>Email</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {centres.map((centre) => (
                  <tr key={centre.id}>
                    <td className="font-medium">{centre.name}</td>
                    <td>{centre.address}</td>
                    <td>{centre.phone}</td>
                    <td>{centre.email}</td>
                    <td>
                      <span className={`status-badge ${centre.is_active ? 'status-completed' : 'status-pending'}`}>
                        {centre.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

const RadiologistsManagement = () => {
  const [radiologists, setRadiologists] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRadiologists();
  }, []);

  const fetchRadiologists = async () => {
    try {
      const response = await axios.get("/users?role=radiologist");
      setRadiologists(response.data);
    } catch (error) {
      console.error("Failed to fetch radiologists:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center"><div className="spinner mx-auto"></div></div>;
  }

  return (
    <div className="space-y-6" data-testid="radiologists-management">
      <div>
        <h1 className="text-3xl font-bold text-slate-800 mb-2">Radiologists</h1>
        <p className="text-slate-600">Manage radiologists across all centres</p>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Phone</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {radiologists.map((rad) => (
                  <tr key={rad.id}>
                    <td className="font-medium">{rad.name}</td>
                    <td>{rad.email}</td>
                    <td>{rad.phone || 'N/A'}</td>
                    <td>
                      <span className={`status-badge ${rad.is_active ? 'status-completed' : 'status-pending'}`}>
                        {rad.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

const StudiesView = () => {
  const [studies, setStudies] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStudies();
  }, []);

  const fetchStudies = async () => {
    try {
      const response = await axios.get("/studies");
      setStudies(response.data);
    } catch (error) {
      console.error("Failed to fetch studies:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (searchParams) => {
    try {
      const response = await axios.post("/studies/search", searchParams);
      setStudies(response.data);
    } catch (error) {
      console.error("Search failed:", error);
    }
  };

  const handleSearchReset = () => {
    fetchStudies();
  };

  if (loading) {
    return <div className="p-8 text-center"><div className="spinner mx-auto"></div></div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-800 mb-2">All Studies</h1>
        <p className="text-slate-600">View all DICOM studies across all centres</p>
      </div>

      <AdvancedSearch onSearch={handleSearch} onReset={handleSearchReset} />

      <Card>
        <CardContent className="p-0">
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Study ID</th>
                  <th>Patient Name</th>
                  <th>Modality</th>
                  <th>Age/Gender</th>
                  <th>Status</th>
                  <th>Uploaded</th>
                </tr>
              </thead>
              <tbody>
                {studies.map((study) => (
                  <tr key={study.id}>
                    <td className="font-mono font-medium">{study.study_id}</td>
                    <td>{study.patient_name}</td>
                    <td><span className="px-2 py-1 rounded bg-slate-100 text-slate-700 text-sm font-medium">{study.modality}</span></td>
                    <td>{study.patient_age}Y / {study.patient_gender}</td>
                    <td>
                      <span className={`status-badge status-${study.status}`}>
                        {study.status}
                      </span>
                    </td>
                    <td>{new Date(study.uploaded_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

// Billing Management Component
const BillingManagement = () => {
  const [activeTab, setActiveTab] = useState('rates');
  const [rates, setRates] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showCreateRateDialog, setShowCreateRateDialog] = useState(false);
  const [newRate, setNewRate] = useState({
    modality: '',
    base_rate: '',
    currency: 'USD',
    description: ''
  });

  useEffect(() => {
    if (activeTab === 'rates') {
      fetchRates();
    } else if (activeTab === 'invoices') {
      fetchInvoices();
    } else if (activeTab === 'transactions') {
      fetchTransactions();
    }
  }, [activeTab]);

  const fetchRates = async () => {
    setLoading(true);
    try {
      const response = await axios.get("/billing/rates");
      setRates(response.data);
    } catch (error) {
      console.error("Failed to fetch billing rates:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchInvoices = async () => {
    setLoading(true);
    try {
      const response = await axios.get("/billing/invoices");
      setInvoices(response.data);
    } catch (error) {
      console.error("Failed to fetch invoices:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchTransactions = async () => {
    setLoading(true);
    try {
      const response = await axios.get("/billing/transactions");
      setTransactions(response.data);
    } catch (error) {
      console.error("Failed to fetch transactions:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRate = async () => {
    try {
      const response = await axios.post("/billing/rates", {
        modality: newRate.modality,
        base_rate: parseFloat(newRate.base_rate),
        currency: newRate.currency,
        description: newRate.description
      });
      
      setRates([...rates, response.data]);
      setShowCreateRateDialog(false);
      setNewRate({ modality: '', base_rate: '', currency: 'USD', description: '' });
    } catch (error) {
      console.error("Failed to create billing rate:", error);
    }
  };

  const handleGenerateInvoice = async (centreId) => {
    try {
      const endDate = new Date();
      const startDate = new Date();
      startDate.setMonth(startDate.getMonth() - 1);
      
      const response = await axios.post("/billing/invoices/generate", {
        centre_id: centreId,
        period_start: startDate.toISOString().split('T')[0],
        period_end: endDate.toISOString().split('T')[0],
        currency: "USD"
      });
      
      setInvoices([...invoices, response.data]);
    } catch (error) {
      console.error("Failed to generate invoice:", error);
    }
  };

  const handlePayInvoice = async (invoiceId) => {
    try {
      const hostUrl = window.location.origin;
      const response = await axios.post("/billing/checkout/create", {
        invoice_id: invoiceId,
        success_url: `${hostUrl}/admin/billing?payment=success&session_id={CHECKOUT_SESSION_ID}`,
        cancel_url: `${hostUrl}/admin/billing?payment=cancelled`
      });
      
      if (response.data.url) {
        window.location.href = response.data.url;
      }
    } catch (error) {
      console.error("Failed to initiate payment:", error);
    }
  };

  const formatCurrency = (amount, currency = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency
    }).format(amount);
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-slate-800">Billing Management</h1>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-slate-200">
        <nav className="-mb-px flex space-x-8">
          {['rates', 'invoices', 'transactions'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-2 px-1 border-b-2 font-medium text-sm capitalize ${
                activeTab === tab
                  ? 'border-teal-500 text-teal-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
              }`}
            >
              {tab}
            </button>
          ))}
        </nav>
      </div>

      {/* Rates Tab */}
      {activeTab === 'rates' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold text-slate-800">Billing Rates</h2>
            <Dialog open={showCreateRateDialog} onOpenChange={setShowCreateRateDialog}>
              <DialogTrigger asChild>
                <Button className="bg-teal-600 hover:bg-teal-700">
                  <Plus className="w-4 h-4 mr-2" />
                  Add Rate
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Create Billing Rate</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="modality">Modality</Label>
                    <Input
                      id="modality"
                      value={newRate.modality}
                      onChange={(e) => setNewRate({...newRate, modality: e.target.value})}
                      placeholder="e.g., X-RAY, CT, MRI"
                    />
                  </div>
                  <div>
                    <Label htmlFor="base_rate">Base Rate</Label>
                    <Input
                      id="base_rate"
                      type="number"
                      step="0.01"
                      value={newRate.base_rate}
                      onChange={(e) => setNewRate({...newRate, base_rate: e.target.value})}
                      placeholder="0.00"
                    />
                  </div>
                  <div>
                    <Label htmlFor="currency">Currency</Label>
                    <select
                      id="currency"
                      value={newRate.currency}
                      onChange={(e) => setNewRate({...newRate, currency: e.target.value})}
                      className="w-full px-3 py-2 border border-slate-300 rounded-md"
                    >
                      <option value="USD">USD</option>
                      <option value="EUR">EUR</option>
                      <option value="GBP">GBP</option>
                    </select>
                  </div>
                  <div>
                    <Label htmlFor="description">Description</Label>
                    <Input
                      id="description"
                      value={newRate.description}
                      onChange={(e) => setNewRate({...newRate, description: e.target.value})}
                      placeholder="Optional description"
                    />
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={() => setShowCreateRateDialog(false)}>
                      Cancel
                    </Button>
                    <Button onClick={handleCreateRate} className="bg-teal-600 hover:bg-teal-700">
                      Create Rate
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          </div>

          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-50 border-b">
                    <tr>
                      <th className="text-left p-4 font-medium text-slate-600">Modality</th>
                      <th className="text-left p-4 font-medium text-slate-600">Rate</th>
                      <th className="text-left p-4 font-medium text-slate-600">Currency</th>
                      <th className="text-left p-4 font-medium text-slate-600">Description</th>
                      <th className="text-left p-4 font-medium text-slate-600">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loading ? (
                      <tr>
                        <td colSpan="5" className="p-8 text-center text-slate-500">Loading...</td>
                      </tr>
                    ) : rates.length === 0 ? (
                      <tr>
                        <td colSpan="5" className="p-8 text-center text-slate-500">No billing rates found</td>
                      </tr>
                    ) : (
                      rates.map((rate) => (
                        <tr key={rate.id} className="border-b hover:bg-slate-50">
                          <td className="p-4 font-medium">{rate.modality}</td>
                          <td className="p-4">{formatCurrency(rate.base_rate, rate.currency)}</td>
                          <td className="p-4">{rate.currency}</td>
                          <td className="p-4 text-slate-600">{rate.description || '-'}</td>
                          <td className="p-4 text-slate-600">{formatDate(rate.created_at)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Invoices Tab */}
      {activeTab === 'invoices' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold text-slate-800">Invoices</h2>
          </div>

          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-50 border-b">
                    <tr>
                      <th className="text-left p-4 font-medium text-slate-600">Invoice #</th>
                      <th className="text-left p-4 font-medium text-slate-600">Centre</th>
                      <th className="text-left p-4 font-medium text-slate-600">Period</th>
                      <th className="text-left p-4 font-medium text-slate-600">Studies</th>
                      <th className="text-left p-4 font-medium text-slate-600">Amount</th>
                      <th className="text-left p-4 font-medium text-slate-600">Status</th>
                      <th className="text-left p-4 font-medium text-slate-600">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loading ? (
                      <tr>
                        <td colSpan="7" className="p-8 text-center text-slate-500">Loading...</td>
                      </tr>
                    ) : invoices.length === 0 ? (
                      <tr>
                        <td colSpan="7" className="p-8 text-center text-slate-500">No invoices found</td>
                      </tr>
                    ) : (
                      invoices.map((invoice) => (
                        <tr key={invoice.id} className="border-b hover:bg-slate-50">
                          <td className="p-4 font-medium">{invoice.invoice_number}</td>
                          <td className="p-4">{invoice.centre_name}</td>
                          <td className="p-4">
                            {formatDate(invoice.period_start)} - {formatDate(invoice.period_end)}
                          </td>
                          <td className="p-4">{invoice.total_studies}</td>
                          <td className="p-4">{formatCurrency(invoice.total_amount, invoice.currency)}</td>
                          <td className="p-4">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                              invoice.status === 'paid' 
                                ? 'bg-green-100 text-green-800' 
                                : invoice.status === 'overdue'
                                ? 'bg-red-100 text-red-800'
                                : 'bg-yellow-100 text-yellow-800'
                            }`}>
                              {invoice.status}
                            </span>
                          </td>
                          <td className="p-4">
                            {invoice.status === 'pending' && (
                              <Button 
                                size="sm"
                                onClick={() => handlePayInvoice(invoice.id)}
                                className="bg-blue-600 hover:bg-blue-700"
                              >
                                Pay Now
                              </Button>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Transactions Tab */}
      {activeTab === 'transactions' && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-slate-800">Payment Transactions</h2>
          
          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-50 border-b">
                    <tr>
                      <th className="text-left p-4 font-medium text-slate-600">Transaction ID</th>
                      <th className="text-left p-4 font-medium text-slate-600">Amount</th>
                      <th className="text-left p-4 font-medium text-slate-600">Currency</th>
                      <th className="text-left p-4 font-medium text-slate-600">Status</th>
                      <th className="text-left p-4 font-medium text-slate-600">User</th>
                      <th className="text-left p-4 font-medium text-slate-600">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loading ? (
                      <tr>
                        <td colSpan="6" className="p-8 text-center text-slate-500">Loading...</td>
                      </tr>
                    ) : transactions.length === 0 ? (
                      <tr>
                        <td colSpan="6" className="p-8 text-center text-slate-500">No transactions found</td>
                      </tr>
                    ) : (
                      transactions.map((txn) => (
                        <tr key={txn.id} className="border-b hover:bg-slate-50">
                          <td className="p-4 font-mono text-sm">{txn.id.slice(0, 8)}...</td>
                          <td className="p-4">{formatCurrency(txn.amount, txn.currency)}</td>
                          <td className="p-4">{txn.currency}</td>
                          <td className="p-4">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                              txn.payment_status === 'paid' 
                                ? 'bg-green-100 text-green-800' 
                                : txn.payment_status === 'failed'
                                ? 'bg-red-100 text-red-800'
                                : 'bg-yellow-100 text-yellow-800'
                            }`}>
                              {txn.payment_status}
                            </span>
                          </td>
                          <td className="p-4">{txn.user_email}</td>
                          <td className="p-4 text-slate-600">{formatDate(txn.created_at)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

export default function AdminDashboard() {
  const { user, logout } = useContext(AuthContext);

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <Sidebar logout={logout} />
      <div className="flex-1 overflow-y-auto">
        <div className="p-8">
          <div className="mb-6">
            <p className="text-sm text-slate-600">Welcome back,</p>
            <h2 className="text-2xl font-bold text-slate-800">{user?.name}</h2>
          </div>

          <Routes>
            <Route path="/" element={<DashboardHome />} />
            <Route path="/centres" element={<CentresManagement />} />
            <Route path="/radiologists" element={<RadiologistsManagement />} />
            <Route path="/studies" element={<StudiesView />} />
            <Route path="/billing" element={<BillingManagement />} />
          </Routes>
        </div>
      </div>
    </div>
  );
}