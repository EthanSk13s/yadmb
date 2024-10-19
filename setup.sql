-- Database generated with pgModeler (PostgreSQL Database Modeler).
-- pgModeler version: 1.1.4
-- PostgreSQL version: 16.0
-- Project Site: pgmodeler.io
-- Model Author: ---

-- Database creation must be performed outside a multi lined SQL file. 
-- These commands were put in this file only as a convenience.
-- 
-- object: yadmbdb | type: DATABASE --
-- DROP DATABASE IF EXISTS yadmbdb;
-- CREATE DATABASE yadmbdb;
-- ddl-end --


-- object: public.song | type: TABLE --
-- DROP TABLE IF EXISTS public.song CASCADE;
CREATE TABLE public.song (
	song_id serial NOT NULL,
	song_name text NOT NULL,
	song_path text NOT NULL,
	album_id integer,
	artist_id integer,
	CONSTRAINT song_pk PRIMARY KEY (song_id)
);
-- ddl-end --


-- object: public.artist | type: TABLE --
-- DROP TABLE IF EXISTS public.artist CASCADE;
CREATE TABLE public.artist (
	artist_id serial NOT NULL,
	artist_name text NOT NULL,
	CONSTRAINT artist_pk PRIMARY KEY (artist_id)
);
-- ddl-end --


-- object: public.album | type: TABLE --
-- DROP TABLE IF EXISTS public.album CASCADE;
CREATE TABLE public.album (
	album_id serial NOT NULL,
	album_name text,
	CONSTRAINT album_pk PRIMARY KEY (album_id)
);
-- ddl-end --


-- object: public.playlist | type: TABLE --
-- DROP TABLE IF EXISTS public.playlist CASCADE;
CREATE TABLE public.playlist (
	playlist_id serial NOT NULL,
	guild_id bigint,
	user_id bigint,
	playlist_name text,
	CONSTRAINT playlist_pk PRIMARY KEY (playlist_id)
);
-- ddl-end --


-- object: public.tracks | type: TABLE --
-- DROP TABLE IF EXISTS public.tracks CASCADE;
CREATE TABLE public.tracks (
	track_id serial NOT NULL,
	track_name text,
	track_uri text,
	CONSTRAINT tracks_pk PRIMARY KEY (track_id)
);
-- ddl-end --


-- object: public.playlist_tracks | type: TABLE --
-- DROP TABLE IF EXISTS public.playlist_tracks CASCADE;
CREATE TABLE public.playlist_tracks (
	playlist_track_id serial NOT NULL,
	playlist_id integer NOT NULL,
	track_id integer NOT NULL,
	CONSTRAINT playlist_tracks_pk PRIMARY KEY (playlist_id,track_id,playlist_track_id)
);
-- ddl-end --

-- object: "FK_ARTIST_SONG" | type: CONSTRAINT --
-- ALTER TABLE public.song DROP CONSTRAINT IF EXISTS "FK_ARTIST_SONG" CASCADE;
ALTER TABLE public.song ADD CONSTRAINT "FK_ARTIST_SONG" FOREIGN KEY (artist_id)
REFERENCES public.artist (artist_id) MATCH SIMPLE
ON DELETE NO ACTION ON UPDATE NO ACTION;
-- ddl-end --

-- object: "FK_ALBUM_SONG" | type: CONSTRAINT --
-- ALTER TABLE public.song DROP CONSTRAINT IF EXISTS "FK_ALBUM_SONG" CASCADE;
ALTER TABLE public.song ADD CONSTRAINT "FK_ALBUM_SONG" FOREIGN KEY (album_id)
REFERENCES public.album (album_id) MATCH SIMPLE
ON DELETE NO ACTION ON UPDATE NO ACTION;
-- ddl-end --

-- object: "PKFK_PLAYLIST_PLAYLIST_TRACK" | type: CONSTRAINT --
-- ALTER TABLE public.playlist_tracks DROP CONSTRAINT IF EXISTS "PKFK_PLAYLIST_PLAYLIST_TRACK" CASCADE;
ALTER TABLE public.playlist_tracks ADD CONSTRAINT "PKFK_PLAYLIST_PLAYLIST_TRACK" FOREIGN KEY (playlist_id)
REFERENCES public.playlist (playlist_id) MATCH SIMPLE
ON DELETE NO ACTION ON UPDATE NO ACTION;
-- ddl-end --

-- object: "PKFK_TRACK_PLAYLIST_TRACK" | type: CONSTRAINT --
-- ALTER TABLE public.playlist_tracks DROP CONSTRAINT IF EXISTS "PKFK_TRACK_PLAYLIST_TRACK" CASCADE;
ALTER TABLE public.playlist_tracks ADD CONSTRAINT "PKFK_TRACK_PLAYLIST_TRACK" FOREIGN KEY (track_id)
REFERENCES public.tracks (track_id) MATCH SIMPLE
ON DELETE NO ACTION ON UPDATE NO ACTION;
-- ddl-end --


