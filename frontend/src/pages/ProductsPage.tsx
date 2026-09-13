import { useEffect, useState } from 'react';
import { Plus, Search, Package as PackageIcon, Edit2, Trash2 } from 'lucide-react';
import { productsApi } from '@/services/api';
import { useAuthStore } from '@/store/authStore';
import type { Product, ProductListResponse } from '@/types';

export default function ProductsPage() {
  const { user } = useAuthStore();
  const [data, setData] = useState<ProductListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', category: '', brand: '', barcode: '', manufacturer_name: '' });
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try { setData(await productsApi.list({ search: search || undefined })); }
    catch {} finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [search]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await productsApi.create(form);
      setShowForm(false);
      setForm({ name: '', category: '', brand: '', barcode: '', manufacturer_name: '' });
      load();
    } catch {}
    finally { setSaving(false); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this product?')) return;
    await productsApi.delete(id);
    load();
  };

  return (
    <div className="page-container">
      <div className="page-header flex items-start justify-between">
        <div>
          <h1 className="page-title">Products</h1>
          <p className="page-subtitle">Product repository for inspected commodities</p>
        </div>
        {(user?.role === 'ADMIN' || user?.role === 'INSPECTOR') && (
          <button onClick={() => setShowForm(true)} className="btn-primary">
            <Plus size={15} />
            Add Product
          </button>
        )}
      </div>

      {/* Search */}
      <div className="relative mb-5 max-w-md">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
        <input
          id="search-products"
          type="text"
          placeholder="Search products..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="form-input pl-9"
        />
      </div>

      {/* Add product form */}
      {showForm && (
        <div className="card-static mb-5">
          <h2 className="text-sm font-semibold text-white mb-4">New Product</h2>
          <form onSubmit={handleCreate} className="grid grid-cols-2 gap-4">
            <div className="form-group col-span-2">
              <label className="form-label">Product Name *</label>
              <input required value={form.name} onChange={(e) => setForm(p => ({...p, name: e.target.value}))} className="form-input" placeholder="e.g., Basmati Rice 5kg" />
            </div>
            <div className="form-group">
              <label className="form-label">Category</label>
              <input value={form.category} onChange={(e) => setForm(p => ({...p, category: e.target.value}))} className="form-input" placeholder="Food & Beverages" />
            </div>
            <div className="form-group">
              <label className="form-label">Brand</label>
              <input value={form.brand} onChange={(e) => setForm(p => ({...p, brand: e.target.value}))} className="form-input" placeholder="Brand name" />
            </div>
            <div className="form-group">
              <label className="form-label">Barcode</label>
              <input value={form.barcode} onChange={(e) => setForm(p => ({...p, barcode: e.target.value}))} className="form-input" placeholder="EAN-13 / UPC" />
            </div>
            <div className="form-group">
              <label className="form-label">Manufacturer</label>
              <input value={form.manufacturer_name} onChange={(e) => setForm(p => ({...p, manufacturer_name: e.target.value}))} className="form-input" placeholder="Manufacturer name" />
            </div>
            <div className="col-span-2 flex gap-3 justify-end">
              <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">Cancel</button>
              <button type="submit" disabled={saving} className="btn-primary">
                {saving ? 'Saving...' : 'Save Product'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Products grid */}
      {loading ? (
        <div className="flex items-center justify-center h-64"><div className="spinner h-8 w-8" /></div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {data?.items.length === 0 && (
            <div className="col-span-full text-center py-20 text-slate-500">
              <PackageIcon size={40} className="mx-auto mb-3 opacity-30" />
              No products found. Add your first product.
            </div>
          )}
          {data?.items.map((product) => (
            <div key={product.id} className="card group">
              <div className="flex items-start justify-between mb-3">
                <div className="w-9 h-9 rounded-lg bg-indigo-500/10 flex items-center justify-center">
                  <PackageIcon size={16} className="text-indigo-400" />
                </div>
                {user?.role === 'ADMIN' && (
                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button onClick={() => handleDelete(product.id)} className="btn-icon text-red-400 hover:text-red-300">
                      <Trash2 size={13} />
                    </button>
                  </div>
                )}
              </div>
              <h3 className="text-sm font-semibold text-white truncate">{product.name}</h3>
              {product.brand && <p className="text-xs text-slate-400 mt-0.5">{product.brand}</p>}
              {product.category && (
                <span className="mt-2 inline-block text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 font-medium">
                  {product.category}
                </span>
              )}
              {product.barcode && (
                <p className="text-xs text-slate-500 mt-2 font-mono">{product.barcode}</p>
              )}
              {product.manufacturer_name && (
                <p className="text-xs text-slate-500 mt-1 truncate">{product.manufacturer_name}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
