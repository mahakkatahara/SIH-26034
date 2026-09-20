--
-- PostgreSQL database dump
--

\restrict E3mtFCBKXtO9CoXP4xEgGhraRI3HyPQxmogUXWvGEBU9Gc2hqrxkdCOv4RkHTQW

-- Dumped from database version 15.19
-- Dumped by pg_dump version 15.19

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: compliance_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.compliance_status AS ENUM (
    'COMPLIANT',
    'NON_COMPLIANT',
    'WARNING',
    'NEEDS_REVIEW',
    'PENDING'
);


--
-- Name: image_label; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.image_label AS ENUM (
    'FRONT',
    'BACK',
    'SIDE',
    'TOP',
    'BOTTOM',
    'OTHER'
);


--
-- Name: inspection_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.inspection_status AS ENUM (
    'DRAFT',
    'IN_PROGRESS',
    'ANALYSIS_PENDING',
    'ANALYSIS_COMPLETE',
    'COMPLETED',
    'CANCELLED'
);


--
-- Name: pipeline_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.pipeline_status AS ENUM (
    'NOT_STARTED',
    'PREPROCESSING',
    'OCR',
    'EXTRACTION',
    'RULE_CHECK',
    'COMPLETED',
    'FAILED',
    'DEV_STUB'
);


--
-- Name: processing_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.processing_status AS ENUM (
    'PENDING',
    'PROCESSING',
    'COMPLETED',
    'FAILED',
    'STUB'
);


--
-- Name: report_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.report_status AS ENUM (
    'PENDING',
    'GENERATING',
    'COMPLETED',
    'FAILED',
    'STUB'
);


--
-- Name: report_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.report_type AS ENUM (
    'PDF',
    'DOCX'
);


--
-- Name: user_role; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.user_role AS ENUM (
    'ADMIN',
    'INSPECTOR',
    'VIEWER'
);


--
-- Name: violation_severity; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.violation_severity AS ENUM (
    'HIGH',
    'MEDIUM',
    'LOW',
    'INFO'
);


--
-- Name: violation_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.violation_status AS ENUM (
    'OPEN',
    'ACKNOWLEDGED',
    'RESOLVED',
    'FALSE_POSITIVE'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: declarations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.declarations (
    id uuid NOT NULL,
    inspection_id uuid NOT NULL,
    image_id uuid,
    field_name character varying(100) NOT NULL,
    field_value text,
    raw_text text,
    confidence_score double precision,
    bounding_box jsonb,
    extraction_method character varying(100),
    is_verified boolean NOT NULL,
    verified_by_id uuid,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: inspection_images; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inspection_images (
    id uuid NOT NULL,
    inspection_id uuid NOT NULL,
    image_path character varying(1000) NOT NULL,
    label public.image_label NOT NULL,
    original_filename character varying(500),
    file_size bigint,
    mime_type character varying(100),
    width integer,
    height integer,
    processing_status public.processing_status NOT NULL,
    processed_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: inspections; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inspections (
    id uuid NOT NULL,
    inspection_number character varying(50) NOT NULL,
    status public.inspection_status NOT NULL,
    overall_compliance_status public.compliance_status NOT NULL,
    product_id uuid,
    inspector_id uuid NOT NULL,
    ai_pipeline_status public.pipeline_status NOT NULL,
    ai_confidence_score double precision,
    remarks text,
    location character varying(500),
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: ocr_regions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ocr_regions (
    id uuid NOT NULL,
    inspection_id uuid NOT NULL,
    image_id uuid,
    text text NOT NULL,
    confidence_score double precision,
    bounding_box jsonb,
    language character varying(50),
    created_at timestamp with time zone NOT NULL
);


--
-- Name: products; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.products (
    id uuid NOT NULL,
    name character varying(500) NOT NULL,
    category character varying(255),
    brand character varying(255),
    barcode character varying(100),
    description text,
    manufacturer_name character varying(500),
    manufacturer_address text,
    country_of_origin character varying(100),
    created_by_id uuid,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: reports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reports (
    id uuid NOT NULL,
    inspection_id uuid NOT NULL,
    report_type public.report_type NOT NULL,
    file_path character varying(1000),
    generation_status public.report_status NOT NULL,
    generated_by_id uuid,
    generated_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: rules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rules (
    id uuid NOT NULL,
    rule_id character varying(50) NOT NULL,
    field character varying(100) NOT NULL,
    category character varying(255),
    mandatory boolean NOT NULL,
    severity public.violation_severity NOT NULL,
    description text NOT NULL,
    validation_logic jsonb,
    legal_reference text,
    rule_version character varying(20) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    package_type character varying(20) DEFAULT 'retail'::character varying NOT NULL,
    citation_verified boolean DEFAULT false NOT NULL
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid NOT NULL,
    email character varying(255) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    full_name character varying(255) NOT NULL,
    role public.user_role NOT NULL,
    employee_id character varying(100),
    department character varying(255),
    phone character varying(20),
    is_active boolean NOT NULL,
    last_login timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: violations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.violations (
    id uuid NOT NULL,
    inspection_id uuid NOT NULL,
    rule_id uuid,
    declaration_id uuid,
    severity public.violation_severity NOT NULL,
    status public.violation_status NOT NULL,
    description text NOT NULL,
    legal_reference text,
    evidence_region jsonb,
    notes text,
    resolved_at timestamp with time zone,
    resolved_by_id uuid,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: declarations declarations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.declarations
    ADD CONSTRAINT declarations_pkey PRIMARY KEY (id);


--
-- Name: inspection_images inspection_images_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inspection_images
    ADD CONSTRAINT inspection_images_pkey PRIMARY KEY (id);


--
-- Name: inspections inspections_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inspections
    ADD CONSTRAINT inspections_pkey PRIMARY KEY (id);


--
-- Name: ocr_regions ocr_regions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ocr_regions
    ADD CONSTRAINT ocr_regions_pkey PRIMARY KEY (id);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- Name: reports reports_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reports
    ADD CONSTRAINT reports_pkey PRIMARY KEY (id);


--
-- Name: rules rules_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rules
    ADD CONSTRAINT rules_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: violations violations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.violations
    ADD CONSTRAINT violations_pkey PRIMARY KEY (id);


--
-- Name: ix_declarations_field_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_declarations_field_name ON public.declarations USING btree (field_name);


--
-- Name: ix_inspections_inspection_number; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_inspections_inspection_number ON public.inspections USING btree (inspection_number);


--
-- Name: ix_ocr_regions_image_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ocr_regions_image_id ON public.ocr_regions USING btree (image_id);


--
-- Name: ix_ocr_regions_inspection_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ocr_regions_inspection_id ON public.ocr_regions USING btree (inspection_id);


--
-- Name: ix_products_barcode; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_products_barcode ON public.products USING btree (barcode);


--
-- Name: ix_products_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_products_category ON public.products USING btree (category);


--
-- Name: ix_rules_field; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_rules_field ON public.rules USING btree (field);


--
-- Name: ix_rules_rule_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_rules_rule_id ON public.rules USING btree (rule_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: declarations declarations_image_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.declarations
    ADD CONSTRAINT declarations_image_id_fkey FOREIGN KEY (image_id) REFERENCES public.inspection_images(id) ON DELETE SET NULL;


--
-- Name: declarations declarations_inspection_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.declarations
    ADD CONSTRAINT declarations_inspection_id_fkey FOREIGN KEY (inspection_id) REFERENCES public.inspections(id) ON DELETE CASCADE;


--
-- Name: declarations declarations_verified_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.declarations
    ADD CONSTRAINT declarations_verified_by_id_fkey FOREIGN KEY (verified_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: inspection_images inspection_images_inspection_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inspection_images
    ADD CONSTRAINT inspection_images_inspection_id_fkey FOREIGN KEY (inspection_id) REFERENCES public.inspections(id) ON DELETE CASCADE;


--
-- Name: inspections inspections_inspector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inspections
    ADD CONSTRAINT inspections_inspector_id_fkey FOREIGN KEY (inspector_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: inspections inspections_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inspections
    ADD CONSTRAINT inspections_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE RESTRICT;


--
-- Name: ocr_regions ocr_regions_image_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ocr_regions
    ADD CONSTRAINT ocr_regions_image_id_fkey FOREIGN KEY (image_id) REFERENCES public.inspection_images(id) ON DELETE SET NULL;


--
-- Name: ocr_regions ocr_regions_inspection_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ocr_regions
    ADD CONSTRAINT ocr_regions_inspection_id_fkey FOREIGN KEY (inspection_id) REFERENCES public.inspections(id) ON DELETE CASCADE;


--
-- Name: products products_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: reports reports_generated_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reports
    ADD CONSTRAINT reports_generated_by_id_fkey FOREIGN KEY (generated_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: reports reports_inspection_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reports
    ADD CONSTRAINT reports_inspection_id_fkey FOREIGN KEY (inspection_id) REFERENCES public.inspections(id) ON DELETE CASCADE;


--
-- Name: violations violations_declaration_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.violations
    ADD CONSTRAINT violations_declaration_id_fkey FOREIGN KEY (declaration_id) REFERENCES public.declarations(id) ON DELETE SET NULL;


--
-- Name: violations violations_inspection_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.violations
    ADD CONSTRAINT violations_inspection_id_fkey FOREIGN KEY (inspection_id) REFERENCES public.inspections(id) ON DELETE CASCADE;


--
-- Name: violations violations_resolved_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.violations
    ADD CONSTRAINT violations_resolved_by_id_fkey FOREIGN KEY (resolved_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: violations violations_rule_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.violations
    ADD CONSTRAINT violations_rule_id_fkey FOREIGN KEY (rule_id) REFERENCES public.rules(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

\unrestrict E3mtFCBKXtO9CoXP4xEgGhraRI3HyPQxmogUXWvGEBU9Gc2hqrxkdCOv4RkHTQW

