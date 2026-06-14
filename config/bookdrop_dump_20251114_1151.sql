--
-- PostgreSQL database dump
--

-- Dumped from database version 15.8 (Debian 15.8-1.pgdg110+1)
-- Dumped by pg_dump version 15.8 (Debian 15.8-1.pgdg110+1)

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
-- Name: tiger; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA tiger;


--
-- Name: tiger_data; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA tiger_data;


--
-- Name: topology; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA topology;


--
-- Name: SCHEMA topology; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA topology IS 'PostGIS Topology schema';


--
-- Name: fuzzystrmatch; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS fuzzystrmatch WITH SCHEMA public;


--
-- Name: EXTENSION fuzzystrmatch; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION fuzzystrmatch IS 'determine similarities and distance between strings';


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: postgis; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


--
-- Name: EXTENSION postgis; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION postgis IS 'PostGIS geometry and geography spatial types and functions';


--
-- Name: postgis_tiger_geocoder; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder WITH SCHEMA tiger;


--
-- Name: EXTENSION postgis_tiger_geocoder; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION postgis_tiger_geocoder IS 'PostGIS tiger geocoder and reverse geocoder';


--
-- Name: postgis_topology; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis_topology WITH SCHEMA topology;


--
-- Name: EXTENSION postgis_topology; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION postgis_topology IS 'PostGIS topology spatial types and functions';


--
-- Name: book_location; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.book_location AS ENUM (
    'library',
    'transit',
    'locker',
    'borrowed'
);


--
-- Name: TYPE book_location; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TYPE public.book_location IS 'Physical location of a book copy.';


--
-- Name: cart_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.cart_status AS ENUM (
    'active',
    'submitted'
);


--
-- Name: TYPE cart_status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TYPE public.cart_status IS 'Shopping cart lifecycle.';


--
-- Name: order_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.order_status AS ENUM (
    'new',
    'prepared',
    'in_transit',
    'ready_for_pickup',
    'picked_up',
    'return_in_progress',
    'returned',
    'canceled'
);


--
-- Name: TYPE order_status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TYPE public.order_status IS 'Lifecycle of an order.';


--
-- Name: shipment_mode; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.shipment_mode AS ENUM (
    'delivery',
    'return'
);


--
-- Name: TYPE shipment_mode; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TYPE public.shipment_mode IS 'Shipment direction: delivery or return.';


--
-- Name: shipment_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.shipment_status AS ENUM (
    'created',
    'placed_in_locker',
    'retrieved_by_user',
    'collected_by_courier',
    'completed'
);


--
-- Name: TYPE shipment_status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TYPE public.shipment_status IS 'Stages of a shipment process.';


--
-- Name: user_role; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.user_role AS ENUM (
    'reader',
    'librarian',
    'courier'
);


--
-- Name: TYPE user_role; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TYPE public.user_role IS 'User role in the system.';


--
-- Name: auto_close_old_carts(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.auto_close_old_carts() RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
  UPDATE cart
  SET status = 'submitted'
  WHERE status = 'active'
    AND created_at < NOW() - INTERVAL '30 days';
END;
$$;


--
-- Name: enforce_lowercase_email(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.enforce_lowercase_email() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  NEW.email := LOWER(NEW.email);
  RETURN NEW;
END;
$$;


--
-- Name: generate_pickup_code(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.generate_pickup_code() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  IF NEW.pickup_code IS NULL THEN
    NEW.pickup_code := substring(encode(gen_random_bytes(6), 'hex') from 1 for 8);
  END IF;
  RETURN NEW;
END;
$$;


--
-- Name: sync_book_item_availability(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.sync_book_item_availability() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  -- Ignoruj rekordy bez przypisanego egzemplarza
  IF (TG_OP = 'INSERT' AND NEW.book_item_id IS NULL)
     OR (TG_OP = 'UPDATE' AND NEW.book_item_id IS NULL)
     OR (TG_OP = 'DELETE' AND OLD.book_item_id IS NULL) THEN
    RETURN NEW;
  END IF;

  IF TG_OP = 'INSERT' THEN
    UPDATE book_item
    SET is_available = FALSE,
        current_location = 'borrowed'
    WHERE id = NEW.book_item_id;

  ELSIF TG_OP = 'UPDATE' AND NEW.returned_at IS NOT NULL THEN
    UPDATE book_item
    SET is_available = TRUE,
        current_location = 'library'
    WHERE id = NEW.book_item_id;

  ELSIF TG_OP = 'DELETE' THEN
    UPDATE book_item
    SET is_available = TRUE,
        current_location = 'library'
    WHERE id = OLD.book_item_id;
  END IF;

  RETURN NEW;
END;
$$;


--
-- Name: update_cart_timestamp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_cart_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$;


--
-- Name: update_order_timestamp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_order_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: book; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.book (
    isbn text NOT NULL,
    title text NOT NULL,
    authors text NOT NULL,
    publisher text,
    published_date text,
    thumbnail text,
    description text,
    source text
);


--
-- Name: TABLE book; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.book IS 'Books available in the library catalog.';


--
-- Name: COLUMN book.source; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.book.source IS 'Data source: manual | open_library | google_books.';


--
-- Name: book_item; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.book_item (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    isbn text NOT NULL,
    is_available boolean DEFAULT true NOT NULL,
    current_location public.book_location DEFAULT 'library'::public.book_location NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: TABLE book_item; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.book_item IS 'Physical copies of books.';


--
-- Name: cart; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cart (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    status public.cart_status DEFAULT 'active'::public.cart_status NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: TABLE cart; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.cart IS 'User shopping carts. Each user may have multiple carts (historical or active), but only one ACTIVE at a time.';


--
-- Name: COLUMN cart.user_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.cart.user_id IS 'Each user can have multiple carts; only one may be ACTIVE at a time.';


--
-- Name: cart_item; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cart_item (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    cart_id uuid NOT NULL,
    isbn text NOT NULL,
    quantity integer DEFAULT 1 NOT NULL,
    added_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT cart_item_quantity_check CHECK ((quantity > 0))
);


--
-- Name: TABLE cart_item; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.cart_item IS 'Books added to user cart. No physical copy assigned yet.';


--
-- Name: locker; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.locker (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    locker_code text NOT NULL,
    street text NOT NULL,
    city text NOT NULL,
    postal_code character varying(10) NOT NULL,
    location public.geography(Point,4326) NOT NULL
);


--
-- Name: TABLE locker; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.locker IS 'Lockers used for book deliveries and returns.';


--
-- Name: locker_box; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.locker_box (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    locker_id uuid NOT NULL,
    number integer NOT NULL,
    is_available boolean DEFAULT true NOT NULL,
    CONSTRAINT locker_box_number_check CHECK ((number > 0))
);


--
-- Name: TABLE locker_box; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.locker_box IS 'Individual boxes inside a locker.';


--
-- Name: locker_shipment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.locker_shipment (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    order_id uuid NOT NULL,
    locker_box_id uuid NOT NULL,
    mode public.shipment_mode NOT NULL,
    status public.shipment_status NOT NULL,
    pickup_code character varying(8),
    placed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_pickup_code_length CHECK (((pickup_code IS NULL) OR (char_length((pickup_code)::text) = 8)))
);


--
-- Name: TABLE locker_shipment; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.locker_shipment IS 'Logistics operations: deliveries and returns.';


--
-- Name: order; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."order" (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    reader_id uuid NOT NULL,
    status public.order_status DEFAULT 'new'::public.order_status NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone
);


--
-- Name: TABLE "order"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public."order" IS 'Formalized book order created from cart contents.';


--
-- Name: order_item; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.order_item (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    order_id uuid NOT NULL,
    book_item_id uuid,
    due_date timestamp with time zone,
    returned_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_order_dates CHECK (((returned_at IS NULL) OR (returned_at >= due_date)))
);


--
-- Name: TABLE order_item; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.order_item IS 'Each record = one borrowed physical copy with return tracking.';


--
-- Name: user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."user" (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email text NOT NULL,
    password text NOT NULL,
    role public.user_role NOT NULL,
    first_name text NOT NULL,
    last_name text NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: TABLE "user"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public."user" IS 'System users (readers, librarians, couriers).';


--
-- Data for Name: book; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.book (isbn, title, authors, publisher, published_date, thumbnail, description, source) FROM stdin;
9788323396949	Literatura polsko-żydowska 1861-1918	Zuzanna Kołodziejska-Smagała, Maria Antosik-Piela 	Wydawnictwo UJ	2017	http://books.google.com/books/content?id=DG5UDwAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	W tomie, który jest rezultatem wieloletnich kwerend i studiów Redaktorek, po raz pierwszy zaprezentowana została polskiemu czytelnikowi panorama literatury polsko-żydowskiej powstającej w latach 1861–1918 – twórczości dotąd niewznawianej, mało znanej i rzadko badanej. Panorama ta ma kilka istotnych wymiarów. Po pierwsze, otrzymujemy obraz środowiska polsko-żydowskich literatów publikujących swe utwory na łamach prasy żydowskiej w języku polskim, wydawanej w różnych zaborach od lat sześćdziesiątych XIX wieku aż po próg niepodległości. Po drugie, uzyskujemy wgląd w ewolucję i zróżnicowanie ideowe tego środowiska: od formujących się od lat sześćdziesiątych XIX wieku kręgów integracjonistycznych – po syjonistyczne, rosnące w siłę od przełomu wieków. Po trzecie, Autorki książki zaprezentowały rodzajową, gatunkową i tematyczną rozmaitość tej twórczości – od liryki o charakterze społecznym i utworów dydaktycznych dla dzieci, poprzez tendencyjne i rodzajowe obrazki, nowele, opowiadania, aż po dramat o tematyce obyczajowej i politycznej. Po czwarte, w przypadku autorów bardziej znanych czy uznanych – takich jak na przykład Aleksander Kraushar czy Janusz Korczak – Redaktorki zdecydowały się ogłosić utwory nieprzedrukowywane w dotychczasowych edycjach, co przyczynia się do wzbogacenia i zniuansowania wizerunków pisarzy. Z recenzji prof. dr hab. Eugenii Prokop-Janiec	google_books
9788377012086	Nauka szczęścia	Ewa Nowińska	Zlote Mysli	2012-03-29	http://books.google.com/books/content?id=anCtCAAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Czy szczęścia można się nauczyć? Większość ludzi uważa, że szczęście przychodzi przypadkiem i do losowo wybranych osób. O tych, którym się powodzi, mówimy, że sąw czepku urodzone. Tymi myślami i porównaniami unieszczęśliwiamy samych siebie, ponieważ skupiamy się na tym, czego NIE POSIADAMY. Prawda jest taka, że szczęście nie jest czymś, co jest nam dane. Jest to coś, na co można PRACOWAĆ. Wszyscy chcemy być szczęśliwi, często do końca nie znając znaczenia tego słowa wytrychu, za którym może się kryć tak wiele.Przyznam, że z dystansem podchodzę do takich publikacji,gdyż ciągle sama poszukuję swojej definicji szczęścia i często,czytając takie poradniki, mam wrażenie, że ktoś mnie, delikatnie mówiąc, nabiera. Z tą książką jest inaczej. Zapewne wynika to z faktu, że autorka jest coachem. Nie stara się czytelnikowi "wcisnąć" gotowych recept i nie przypisuje sobie monopolu na wiedzę, jak to upragnione szczęście osiągnąć. Wręcz odwrotnie. Próbuje udowodnić, że osiągnięcie szczęścia, czymkolwiek by ono nie było, to owoc systematycznej i ciężkiej pracy nad swoją osobowością. Stojąc z boku, cichym i wyważonym głosem podpowiada nam, na co zwrócić uwagę w swoim życiu oraz jak pokierować naszym myśleniem, codziennym byciem, by żyło się nam pełniej, lżej i w zgodzie z samym sobą.Anna Zalewska, historyk sztuki, kurator wystaw Od autorki: Czasem nie znamy odpowiednich mechanizmów, nie mamy wyrobionych nawyków szczęścia,nie znamy wielu metod, które mogłyby nam pomóc w drodze do naszego celu. Z tego właśnie względu zdecydowałam się na tę publikację by dostarczyć NAUKOWYCH METOD, ułatwiających nam naszą drogę ku szczęściu.	google_books
9783758437830	Nauka jazdy na snowboardzie	C. Oach	epubli	2023-12-02	http://books.google.com/books/content?id=ZD7nEAAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Świeży puch, dźwięk deski sunącej po stoku i poczucie wolności - oto snowboard. "Nauka jazdy na snowboardzie: przewodnik dla początkujących" to bilet do tego ekscytującego świata. Ta książka nie tylko uczy podstaw jazdy na snowboardzie, ale także przygotowuje psychicznie i fizycznie do pierwszych prób na desce. Dowiedz się, jak wybrać odpowiedni sprzęt, jak wykonać pierwsze skręty oraz jak być bezpiecznym i pewnym siebie na stoku. Dołącz do nas w tej podróży i odkryj radość z jazdy na snowboardzie dla siebie.	google_books
9783758443466	Nauka jazdy na nartach	Them Entor	epubli	2023-12-09	http://books.google.com/books/content?id=tmvoEAAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Pokryte śniegiem góry i lśniące stoki czekają na podbój. "Nauka jazdy na nartach: przygody na stoku dla początkujących i ciekawskich" to przewodnik po świecie alpejskiej zabawy. Oferuje solidne wprowadzenie do podstaw narciarstwa, od wyboru sprzętu po właściwą technikę. Dzięki praktycznym ćwiczeniom i cennym wskazówkom, książka ta towarzyszy ci od pierwszych kroków na nartach po pierwsze pełne przygód zjazdy. Odkryj niezrównane uczucie szusowania po stokach i doświadcz magii sportów zimowych z pierwszej ręki.	google_books
9783758438240	Nauka jazdy na rolkach	C. Oach	epubli	2023-12-02	http://books.google.com/books/content?id=eD7nEAAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Płynny ślizg po asfalcie, prędkość, wolność - jazda na rolkach to znacznie więcej niż tylko sport. "Nauka jazdy na rolkach dla początkujących" to idealne wprowadzenie do tego dynamicznego świata. Od podstaw techniki po wskazówki dotyczące bezpieczeństwa: Ta książka towarzyszy ci krok po kroku w drodze do płynnych ruchów i bezpiecznej jazdy. Zrób pierwszy krok, załóż rolki i poczuj dreszczyk emocji związany z tym fascynującym sportem.	google_books
9788364208195	Nauka, metoda, wartości	Mateusz Kotowski, Damian Leszczyński	Polskie Forum Filozoficzne	2022-09-19	http://books.google.com/books/content?id=33mUEAAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Zbiór tekstów dotyczących filozofii.	google_books
9788375823004	Szybka nauka dla wytrwałych. Jak skutecznie rowiązać swoje problemy z nauką	Paweł Sygnowski	Zlote Mysli	2015-03-25	http://books.google.com/books/content?id=Th7FCQAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Poznaj skuteczne techniki pamięciowe, dzięki którym zapamiętasz bez trudu to, czego potrzebujesz do nauki czy pracy. Z książki dowiesz się m.in.: jak działa mózg; jak mózg zapamiętuje informacje; jak działa pamięć; jak poprawić pamięć; jak ułatwić sobie zapamiętywanie; w jaki sposób wiedza o pamięci rozwijała się od starożytności do dzisiaj. Wykorzystaj moc swojego mózgu już dzisiaj! co robić, aby lepiej zapamiętywać	google_books
9783758441387	Nauka gry w szachy	C. Oach	epubli	2023-12-07	http://books.google.com/books/content?id=GzPoEAAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Szachy, królewska gra, od wieków fascynuje ludzi w każdym wieku i z różnych kultur. "Learn Chess: From Beginner to Chess Master" to kompleksowy przewodnik do odkrywania głębi i zawiłości tej ponadczasowej gry. Ta książka prowadzi krok po kroku przez podstawy, od pierwszych ruchów po zaawansowane strategie, które będą wyzwaniem nawet dla najbardziej doświadczonych graczy. Dzięki ilustracyjnym przykładom, jasnym wyjaśnieniom i praktycznym ćwiczeniom nauczysz się przechytrzać przeciwników, udoskonalać swoją technikę i wkroczysz na ścieżkę do zostania mistrzem szachowym.	google_books
9788323128830	Podmiot poznania a nauka	Małgorzata Czarnocka	Wydawnictwo Naukowe Uniwersytetu Mikołaja Kopernika	2012	http://books.google.com/books/content?id=PnjkBgAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Przemyślenia przedstawiane w tej monografii są poświęcone podmiotowi poznania, który w całej epistemologii nowożytnej odgrywał fundamentalną rolę, w filozofii współczesnej zaś, wraz z jej zwrotem ku paradygmatowi lingwistycznemu, został zdyskredytowany, chociaż przy wnikliwych analizach treści oferowanych przez tę filozofię ujawnia swoją obecność, ukazując, że nie można pozbyć się go całkowicie, gdyż zawsze odciska swoje piętno. Szczególnej dyskredytacji podlega podmiot poznania w filozofii nauki, którą ciągle przenika duch neopozytywizmu z jego ograniczeniem dziedziny eksploracji do gotowej wiedzy i jej językowo wyrażonych rezultatów. Chodzi mi głównie, chociaż nie jedynie, o rozpatrzenie roli podmiotu poznania w nauce. Do rozważenia tego problemu trzeba jednak przyjąć epistemologiczną perspektywę, a poznanie naukowe uznać za rodzaj poznania niespecyficzny pod względem teoriopoznawczym. Trzeba mianowicie założyć, że nie wyróżnia się ono spośród innych typów poznania cechami istotny mi teoriopoznawczo, ale podlega jedynie ostrzejszym rygorom metodycznym. Tak więc przyjmuję, że dociekania nad poznaniem naukowym zlewają się z ogólną epistemologią, a trend do izolowania tych dwóch dziedzin problemowych tylko spłyca ujęcia, szczególnie obraz poznania naukowego.	google_books
9788381359764	Historia, której nie było	Agnieszka Jankowiak-Maik	Otwarte	2022-04-27	http://books.google.com/books/content?id=-11xEAAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	TA KSIĄŻKA CAŁKOWICIE ODMIENI TWOJE SPOJRZENIE NA DZIEJE POLSKI! Historia, jaką znasz z podręczników, w dużej części składa się z uproszczeń, manipulacji, przemilczanych faktów, a czasem nawet zwykłych kłamstw. Prawda jest taka, że bitwy pod Psim Polem nie było, Kazimierz Wielki nie umarł bezpotomnie, do chrztu nie przekonała Mieszka jego żona Dobrawa, a w roku 1920 Polacy nie zwyciężyli dzięki „cudowi nad Wisłą”, tylko dzięki znakomitym działaniom naszego wywiadu. Zaskoczeni? A to dopiero początek. Agnieszka Jankowiak-Maik (znana w internecie jako Babka od histy) w lekki sposób pisze o niezwykłych meandrach polskiej historii: ukazuje jej drugie dno, przypomina zapomniane postacie i odkrywa przemilczane wydarzenia. Do tego bezpardonowo obnaża najgłupsze elementy polityki historycznej, która – zniekształcając rzeczywistość – do dziś realizowana jest w szkołach. Jeśli chcesz poznać prawdziwe dzieje naszego kraju i oczyścić umysł ze złogów propagandy, po prostu otwórz tę książkę i zacznij czytać. Agnieszka Jankowiak-Maik jest właścicielką popularnego fanpage’a „Babka od histy”, wiceprezeską Fundacji Muzeum Historii Kobiet, autorką wielu artykułów na portalach Ciekawostki Historyczne i Twoja Historia, a także nauczycielką, która od lat aktywnie działa na rzecz zmiany edukacji w Polsce. Za swoją działalność otrzymała Nagrodę im. Ireny Sendlerowej „Za naprawianie świata”, Medal Wolności Słowa Fundacji Grand Press oraz została Wielkopolskim Nauczycielem Roku 2021. W tym samym roku redakcja „Wysokich Obcasów” uznała ją za jedną z 50 Śmiałych – za sprzeciw wobec reformy edukacji. Mądra, a do tego zabawna książka Agnieszki Jankowiak-Maik raczej nie sprawi, że pokochacie historię Polski miłością ślepą. Da wam coś więcej – spowoduje, że się historią szczerze zainteresujecie, porzucicie pochopne sądy i wygodne mity. Uwaga! Po lekturze można nawet zamarzyć o powrocie do szkoły! Bo kto by nie chciał mieć TAKICH lekcji i TAKIEJ nauczycielki? Ja bardzo bym chciała. Justyna Suchecka-Jadczak, dziennikarka „Oto historia z kantem, co podwójne ma dno”. Babka od histy zagląda pod podszewkę i na zaplecze dziejów, wołając „Sprawdzam!”. I udowadnia, że historia, której nas uczono, to... cóż... tylko historia, której nas uczono. Nie cała i nie jedyna. Ta książka jest jak zadanie z gwiazdką. Tyle że rozwiązane. Anna Kowalczyk, autorka książki „Brakująca połowa dziejów. Krótka historia kobiet na ziemiach polskich” Agnieszka obala wiele popularnych mitów i pozwala spojrzeć na nasze dzieje bardziej obiektywnie. Udowadnia, że to nie tylko daty, ale również cała masa ciekawostek, że historia opowiada nie tylko o mężczyznach, ale także o kobietach. Mój ścisły umysł zachwyciły syntetyczne podsumowania z najważniejszymi informacjami po każdym rozdziale. Nigdy nie myślałem, że książka historyczna może tak wciągnąć chemika. Pan Belfer, panbelfer.pl Jeżeli ktoś by powiedział, że Józef Piłsudski żył w XIII wieku, można by się po prostu uśmiechnąć, traktując taką pomyłkę jak dobry żart. W końcu to jest błąd oczywisty. Dużo poważniejsze są błędy, których nie widać na pierwszy rzut oka. Jakże łatwo je wtedy powtarzać i utrwalać! A gdy utrwalają je podręczniki szkolne, sprawa jest już naprawdę poważna. Agnieszka zrobiła wspaniałą robotę: napisała książkę, która w totalnie merytoryczny i niezwykle interesujący sposób te błędy punktuje – oraz prostuje. Dopóki nie przeczytałem „Historii, której nie było”, nie miałem pojęcia, jak wiele ich jest. Przemek Staroń, psycholog, Nauczyciel Roku 2018, autor serii książek „Szkoła bohaterek i bohaterów”	google_books
9788378594086	Historia Pajączka Robina	Sylwia Gliniewicz	e-bookowo	2014-12-10	http://books.google.com/books/content?id=75_OBQAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	,,Historia Pajączka Robina’’ to opowieść o pajączku, sympatycznym mieszkańcu lasu, który ze względu na swój wygląd i charakter, traktowany jest przez większość zwierząt jak odmieniec.	google_books
9788376706405	Kowal. Prawdziwa historia	Wojciech Kowalczyk, Krzysztof Stanowski	Buchmann	2012-11-14	http://books.google.com/books/content?id=WvRuBgAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Barwna autobiografia jednej z największych legend polskiego futbolu - Wojciecha Kowalczyka - piłkarza Legii i hiszpańskiego Betisu, zawodnika srebrnej jedenastki Janusza Wójcika. Kowalczyk z niespotykaną szczerością przedstawia swoją historię, blaski i cienie polskiego futbolu. Piłka nożna w tej książce jest w sumie pretekstem do pytania: co jest w życiu najważniejsze? - i z pośród kilku odpowiedzi, które daje Kowal futbol wcale nie jest na pierwszym miejscu. Książka mówi tyle o życiu piłkarza, co głośna Futbolowa gorączka Nicka Hornby'ego o życiu kibica.	google_books
9788381105316	Przekleństwo Swietłany. Historia córki Stalina	Beata de Robien	Sonia Draga Sp. z o.o.	2018-04-17	http://books.google.com/books/content?id=a9NVDwAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Przekleństwo Swietłany to intymny portret Swietłany Alliłujewej, córki Józefa Stalina. Autorka śledzi jej losy od dzieciństwa naznaczonego śmiercią matki, skomplikowanymi relacjami z apodyktycznym ojcem, poprzez dramatyczny okres II wojny światowej, nieudane małżeństwa, aż do decyzji o poszukiwaniu azylu i ucieczki do Stanów Zjednoczonych w 1967 roku. Opowiadając o Swietłanie, Beata de Robien kreśli również panoramę historyczną komunistycznej Rosji tamtych lat, pisze o Józefie Stalinie i jego najbliższym otoczeniu. Historia Swietłany stawia przed czytelnikiem szereg pytań: czy możliwe jest normalne życie z piętnem ojca będącego jednym z największych zbrodniarzy w dziejach ludzkości? Czy można wyzbyć się poczucia winy za zbrodnie ojca? Jak mierzyć się z demonami przeszłości?	google_books
9788324036011	Ptaki drapieżne. Historia Lucjana "Sępa" Wiśniewskiego, likwidatora z kontrwywiadu AK	Michał Wójcik, Emil Marat, Lucjan Wiśniewski	Otwarte	2020-03-30	http://books.google.com/books/content?id=5Lg9DwAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Bohater. Mściciel. Egzekutor. Lucjan „Sęp” Wiśniewski – jeden z ostatnich żyjących likwidatorów z Armii Krajowej, żołnierz elitarnego “Wapiennika” - oddziału specjalnego 993/W kontrwywiadu AK, który w latach wojny wykonywał wyroki śmierci wydane przez Państwo Podziemne. Brał udział w ponad 60 egzekucjach zdrajców i konfidentów. Pierwszej dokonał, gdy miał zaledwie 17 lat. W niezwykle szczerej rozmowie „Sęp” opowiada o swoich wojennych przeżyciach i o tym, jak on i jego nastoletni koledzy z “patrolu Ptaków” - pseudonimy brali z atlasu ornitologicznego - zmieniali się z piskląt, bezbronnych chłopców, w drapieżne ptaki, bezwzględnych żołnierzy. Obok nas i przed nami sypią się iskry z jezdni od padających pocisków. Rysiek był przede mną jakieś dwadzieścia metrów. I widzę, że on coraz wolniej biegnie, aż go dogoniłem. Widzę, że jest blady i takim chrapliwym głosem mówi: – Ranny jestem... (...) »Naprawa« się wychylił i zobaczył, że na końcu Mazowieckiej, przy placu Napoleona, stoi oddział Niemców. Wszyscy z karabinami, patrzą w naszą stronę. Położyliśmy »Gila« w bramie, pamiętam, że na jego piersiach pojawiła się plama krwi, która zaczęła rosnąć. Zrobiła się duża. I wtedy jakby poczuliśmy, że to może być koniec... Niebezpieczne pościgi, uliczne strzelaniny, konspiracyjne „wsypy” i tragiczne pomyłki – akcje które opisuje Lucjan „Sęp” Wiśniewski wyglądają niczym sceny wyjęte z brutalnego filmu sensacyjnego, różnica polega na tym, że to działo się naprawdę. Jak wyglądała hierarchia egzekutorów? Czy miewali wyrzuty sumienia? Czy wojna usprawiedliwia wszystkie rozkazy ? Ile likwidatorzy dostawali za „robotę”, czyli zastrzelenie „delikwenta”? Gdzie leży granica między odwagą, brawurą a okrucieństwem?	google_books
9782808694544	Historia o mewie i kocie, który uczył ją latać książka Luis Sepúlveda (Analiza książki)	Johanna Biehler	Primento Digital sprl	2023-05-19	http://books.google.com/books/content?id=l9_AEAAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Czego powinniśmy się nauczyć z Historia o mewie i kocie, który uczył ją latać, opowieści o wzajemnej pomocy, ekologii i odwadze dla młodych i starych? Znajdź wszystko, co musisz wiedzieć o tym dziele w kompletnej i szczegółowej analizie. W tym pliku znajdziesz w szczególności : - Pełne streszczenie - Prezentacja głównych bohaterów takich jak Kengah, dziecko i Zorbas - Analiza specyfiki utworu: gatunek, styl oraz tematyka solidarności, pomocy wzajemnej, tolerancji, ekologii i zachowań ludzkich Analiza źródłowa pozwalająca na szybkie zrozumienie sensu utworu.	google_books
9788727084572	Pielęgniarka - Historia zbrodni, które wstrząsnęły Skandynawią	Kristian Corfixen	Lindhardt og Ringhof	2023-05-22	http://books.google.com/books/content?id=7d_AEAAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	True crime, które stało się hitem Netflixa! Wczesnym rankiem w marcu 2015 roku operator policji odbiera telefon. Pielęgniarka ze Szpitala w Nykøbing Falster podejrzewa koleżankę z pracy o umyślne doprowadzanie do śmierci pacjentów. Kobieta obawia się, że właśnie doszło do kolejnego morderstwa. Wkrótce coraz więcej potencjalnych świadków zarzuca pielęgniarce podawanie pacjentom substancji zagrażających życiu. Tylko dlaczego przez lata milczeli? Czemu nikt nie zareagował? I skąd wziąć dowody, skoro wszystkie ciała zmarłych zostały poddane kremacji? „Pielęgniarka" to wielokrotnie nagrodzony reportaż Kristiana Corfixena. Dziennikarz rekonstruuje wydarzenia z nocnego dyżuru, podczas którego w tajemniczych okolicznościach zmarło troje pacjentów, co zapoczątkowało jedną z najgłośniejszych spraw kryminalnych w historii Danii. Autor przedstawia raporty policyjne, materiały dowodowe oraz dokumentację medyczną i śledczą, by przybliżyć przebieg wydarzeń feralnej nocy oraz ujawnić, co tak naprawdę doprowadziło do skazania pielęgniarki w ramach procesu, który wstrząsnął całą Skandynawią. W „Pielęgniarce" zawarte są wypowiedzi kluczowych dla sprawy osób, w tym skazanej Christiny Aistrup Hansen, która do dziś nie przyznaje się do postawionych zarzutów, i świadka koronnego, Pernille Kurzmanna Larsena. Obydwoje po raz pierwszy zabierają publicznie głos na ten temat. Czy proces duńskiej pielęgniarki to wynik plotek i pomówień czy konsekwencja celowego okrucieństwa wobec pacjentów w pogoni za rozgłosem? Idealna dla fanów kultowego dramatu Netflixa "Ratched"! Kristian Corfixen (ur. 1988) jest dziennikarzem. Za "Pielęgniarkę" zyskał uznanie krytyków i zdobył kilka prestiżowych nagród. Właśnie ten reportaż zapoczątkował dyskusję na temat zaufania, jakim obdarzamy personel medyczny oraz debatę dotyczącą dowodów rzeczowych w procesie karnym. Ta przejmująca książka, napisana w języku duńskim, w latach 2021-2022 zostanie przetłumaczona na dziewięć języków i ukaże się na całym świecie nakładem wydawnictwa Saga Egmont.	google_books
9788328097124	Płeć i mózg. Historia przekręconych faktów	Daphna Joel, Luba Vikhanski	WAB	2022-02-08	http://books.google.com/books/content?id=PZ8SEQAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Czy wiesz, że pół godziny stresu wystarczy, żeby niektóre obszary w mózgu zmieniły płeć z męskiej na żeńską i odwrotnie? Koncepcja męskiego i kobiecego mózgu nawiązuje do popularnego poglądu, który głosi, że mężczyźni i kobiety pochodzą z różnych planet. Ale czy potwierdzają ją badania naukowe? Podjęta przez autorki próba odpowiedzi na to pytanie miała początek w zaskakujących badaniach, które mogą całkowicie zmienić sposób postrzegania płci biologicznej, kulturowo-społecznej oraz mózgu. Nie twierdzę, że nie ma różnic między mózgami kobiecymi a męskimi, przeciwnie – istnieje wiele takich różnic. Twierdzę jednak, że te rozbieżności łączą się w mózgu każdej osoby i tworzą unikatową mozaikę cech, a niektóre z nich występują częściej u kobiet, inne zaś u mężczyzn. Pogląd ten idzie w parze z tym, co ‒ jak jestem przekonana ‒ wie już wiele osób: że wszyscy jesteśmy zlepkiem cech „kobiecych” i „męskich”. Sięga jednak dalej i sugeruje, że nie ma czegoś takiego jak mózg „męski” czy „kobiecy”, ani „męski” czy „kobiecy” charakter. (fragment książki) Daphna Joel - profesorka psychologii i neurobiologii na Uniwersytecie w Tel Awiwie. Swoje doświadczenie neurobiologiczne połączyła z zainteresowaniem naukami o płci. Badaniami, w których neguje istnienie mózgu męskiego i mózgu kobiecego, zrewolucjonizowała myślenie o płci biologicznej, kulturowo-społecznej oraz mózgu. Luba Vikhanski - dziennikarka i wielokrotnie nagradzana autorka publikacji popularnonaukowych. Jej prace ukazywały się m.in. w „The New York Times”, „Nature”, „Medicine” i „The Jerusalem Post”. Jest autorką trzech książek, w tym Immunity: How Elie Metchnikoff Changed the Course of Modern Medicine, która została bardzo dobrze przyjęta przez Brytyjskie Stowarzyszenie Medyczne. Pracuje w Instytucie Nauki Weizmanna. Mieszka w Izraelu.	google_books
9788324079513	Skrzydlata husaria. Historia polskich lotników bombowych	Łukasz Sojka	Znak	2020-12-07	http://books.google.com/books/content?id=x9tzEAAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Bądź świadkiem pierwszego ataku bombowego w historii polskiego lotnictwa podczas walk z Ukraińcami o Lwów. Wystartuj z polskimi lotnikami bombowymi i rusz naprzeciw pancernym dywizjom Hitlera we wrześniu 1939 roku. Spójrz na nocne niebo pełne eksplozji pocisków przeciwlotniczych z wieżyczki tylnego strzelca pokładowego. Usiądź za sterami karasia i stocz nierówną walkę z myśliwcami wroga. Niezwykłe poświęcenie, brawura granicząca z szaleństwem, wiara w zwycięstwo i nieustanne poczucie zagrożenia, któremu trzeba stawić czoła. Dramaturgia pola walki odmalowana z epickim rozmachem i precyzja opisów powietrznych pojedynków – wszystko to serwuje nam autor Skrzydlatej husarii. Znakomicie napisanej historii polskich lotników bombowych. Od pierwszego lotu polskiego bombowca aż do heroicznych powietrznych zmagań kampanii wrześniowej. Lektura obowiązkowa dla wszystkich fanów lotnictwa i miłośników historii. Wojna na morzu i pod powierzchnią wody to historia odwagi marynarzy, geniuszu wojennego dowódców, kaprysów pogody, czasem żołnierskiego szczęścia. Powyższy opis pochodzi od wydawcy.	google_books
9788324044238	Bóg. Ludzka historia religii	Aslan Reza	Otwarte	2021-11-05	http://books.google.com/books/content?id=tV5xEAAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	W Bogu od zawsze szukamy tego, czego nam brakuje: miłości, sprawiedliwości i pocieszenia. Ale przypisujemy Mu także to, czego sami nie potrafimy kontrolować: gniew, chciwość i zazdrość. Stworzyliśmy Boga na nasze podobieństwo i dlatego ta sama religia stanowi dla jednych ludzi źródło pokoju, a dla innych wezwanie do stosowania przemocy. BÓG JEST NASZĄ IDEĄ I OD NAS ZALEŻY, CZY OKAŻE SIĘ DOBRA. Obowiązkowa lektura dla wszystkich, którzy chcą zrozumieć, skąd wzięły się religie i do czego ludzie wykorzystują Boga. Aktualna, porywająca i otwierająca oczy książka. Trzeba ją przeczytać. – „The Huffington Post” Ta niewielkich rozmiarów, ale ambitna opowieść o tym, jak ludzie tworzą Boga przez wielkie „B”, dosłownie oszałamia czytelnika.– „Los Angeles Review of Books” Wyjątkowa, klarowna, oszczędna w słowach, ale żywo opowiedziana historia. – „The Spectator” Reza Aslan – badacz religii i duchowy poszukiwacz, gotowy naruszyć tabu, by zrozumieć ludzi i ich świat. Autor kilku bestsellerowych książek, w tym Nie ma Boga oprócz Allahaoraz Zelota. Życie i czasy Jezusa z Nazaretu. Specjalista od creative writing, a także telewizyjny komentator i prezenter. Dla CNN zrealizował serial dokumentalny pt. Believer. Wcielał się w nim w wyznawców różnych religii, by nie tylko studiować ludzkie wierzenia, ale też doświadczać ich. Wspólnie z Rainnem Wilsonem prowadzi podkast Metaphysical Milkshake, w którym z zaproszonymi gośćmi dyskutują nad najważniejszymi życiowymi pytaniami.	google_books
9782322469536	krótka historia uleglosci spolecznej	Arthur Postré	BoD - Books on Demand	2023-01-05	http://books.google.com/books/content?id=RdylEAAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	W tym krótkim wystapieniu francuski autor, Arthur Postré, opowiada o temacie spolecznego poddanstwa orkiestrowanego od XVI wieku niemal na calym swiecie. Pojawienie sie nowych technologii wydawalo sie byc poczatkiem wolnosci jednostki, wszelkich mozliwosci, ale bylo to zludne zludzenie, które jeszcze bardziej zniewolilo nas do nowych norm i obyczajów, na które spoleczenstwo nie bylo przygotowane. Poznaj rozwiazania, wedlug Arthura Postré, jak stac sie panem siebie i swoich mysli, by stac sie lepszym czlowiekiem. Niemniej jednak proces ten nie jest pozbawiony nierównosci.	google_books
9788727088563	Krótka historia Iwony Tramp	Krystyna Kofta	Lindhardt og Ringhof	2023-07-14	http://books.google.com/books/content?id=jJ7NEAAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Pionierska baśń fantasy, jakiej jeszcze nie było! Przeżyj fascynującą przygodę w nieznanym świecie, stworzonym przez polską społeczność internetową. Iwona, niezależna nastolatka, odkrywa, że marzenia mają swoją cenę, gdy trafia do wielkiego miasta pełnego tajemnic. To wciągająca opowieść o odwadze, wyborach i szybkim dorastaniu. Iwona musi stanąć twarzą w twarz z niebezpiecznym światem, którego nie zna. Czy wybierze dobrą ścieżkę? To książka pełna pytań, która zainspiruje Cię do poszukiwania własnej drogi. Współtwórz historię Iwony i doświadcz prawdziwej magii marzeń! Książka łączy w sobie najlepsze elementy dystopijnych powieści młodzieżowych z elementami baśni, tworząc niepowtarzalną, porywającą opowieść o dorastaniu, wyborach i odkrywaniu prawdziwej siebie. Jeżeli cenisz sobie silne, niezależne bohaterki, które muszą sprostać wyzwaniom w nieznanym świecie, jak Katniss z "Igrzysk Śmierci", to historia Iwony Tramp jest dla Ciebie! Krystyna Kofta - uznana polska pisarka i felietonistka. Pierwszą powieść "Wizjer" wydała w 1978 roku. Znana jest z powieści jak "Ciało niczyje" czy "Faust". W 2007 zdobyła Grand Prix na Festiwalu "Dwa Teatry – Sopot 2008" za słuchowisko "Stare wiedźmy" z Danutą Szaflarską w roli głównej. Od 2013 zasiada w jury Nagrody "Newsweeka" im. Teresy Torańskiej.	google_books
9788324066292	Byłem fotografem w Auschwitz. Prawdziwa historia Wilhelma Brassego	Anna Dobrowolska	Znak	2022-10-11	http://books.google.com/books/content?id=HXyUEAAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Historia człowieka, który fotografował piekło. „Nazywam się Wilhelm Brasse. Jestem fotografem. Od września 1940 roku byłem więźniem w obozie koncentracyjnym w Auschwitz. Wykonałem ponad 50 tysięcy zdjęć do obozowych kartotek oraz dokumentację eksperymentów doktora Mengelego” – tak swoją opowieść zaczyna człowiek, którego zdjęcia stały się dowodem zbrodni przeciw ludzkości. Wilhelm Brasse, dwudziestotrzyletni mężczyzna z Żywca, trafił do Auschwitz. Spędził tam ponad cztery lata i na zlecenie nazistów prowadził dokumentację fotograficzną. Po wojnie jego zdjęcia obiegły cały świat, dając świadectwo tragedii ponad miliona osób. Brasse po tym, co widział w Auschwitz, nigdy nie wrócił do zawodu. Mroczne wspomnienia z obozu nie pozwoliły mu wykonywać zwykłych fotografii. Byłem fotografem w Auschwitz to pierwszoosobowa relacja z obozowego piekła. „Jestem pod dużym wrażeniem tej książki. Nie jest to praca naukowa ani też sensu stricte pamiętnik, ale wnosi bardzo dużo do wiedzy dzisiejszych zwyczajnych ludzi nie tylko o obozie, lecz i o systemie, który takie obozy stworzył.” Władysław Bartoszewski	google_books
9788395522772	Fantastyczne pióra 2019: Antologia portalu fantastyka.pl	Marcelina Baczyńska, Kamila Regel, Sylwester Gdela, Agata Poważyńska, Sonia Korta, Wiktor Orłowski, Marek Kolenda, Agnieszka Fulińska, Dariusz Zasadzki, Aleksandra Klęczar, Paweł Wolski, Katarzyna Szymonik	Fantastyczne Pióra	2021-03-25	http://books.google.com/books/content?id=JhgmEAAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	"To prawdopodobnie jedyna w Polsce antologia z tach surowym przesiewem. O być albo nie być opowiadań decyduje aż dziewięć oczytanych i wymagających osób, które stanowią Lożę NF. Wypadkową ich gustów są właśnie Fantastyczne pióra, udowadniające, że nasz rodzina fantastyka ma się dobrze. Trzeba tylko dopuścić do głosu nowych twórców. Wsłuchajcie się w to, co mają do powiedzenia, i zapamiętajcie nazwiska autorów – ich tekstów tak łatwo nie zapomnicie" – Krzysztof Matkowski	google_books
9788396262554	Fantastyczne pióra 2021. Antologia portalu fantastyka.pl	Jakub Kubal, Jakub Fijałkowski, Krzysztof Rarocki, Radek Puchała, Paweł Wącławski, Sylwester Gdela, Michał Pięta, Mateusz Kędziora, Sylwia Finklińska, Daniel Kordowski, Adam Ciszewski, Irka Luz, Rafał Łoboda	Fantastyczne Pióra	2022-11-25	http://books.google.com/books/content?id=9vqdEAAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Antologia wyróżnionych opowiadań opublikowanych na portalu fantastyka.pl w 2021 roku	google_books
9788323138303	Nie tylko Lem. Fantastyka współczesna	Maciej Wróblewski	Wydawnictwo Naukowe Uniwersytetu Mikołaja Kopernika	2017	http://books.google.com/books/content?id=QVk1DwAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Niniejsza książka przynosi częściową odpowiedź na pytanie o zakres wpływu twórczości literackiej Stanisława Lema na najnowszą polską fantastykę. To bez wątpienia ważny w rozwoju konwencji niewerystycznej wątek, mimo że czytelnicy rodzimej literatury fantastycznej dziś już coraz rzadziej sięgają po prozę Lema. Autor Niezwyciężonego stał się przede wszystkim „marką”, o której niemal każdy kolekcjoner popularnych serii fantasy słyszał, ale niekoniecznie zna jego utwory. Niemniej kondycja literatury fantastycznej, sądząc po jakości utworów zgłaszanych już od dziesięciu lat do Nagrody Literackiej im. Jerzego Żuławskiego, tylko niekiedy rozczarowuje, częściej bywa oceniana wysoko zarówno pod względem artystycznym, jak i intelektualnym. Publikacja, która właśnie trafia do rąk Czytelnika, ma ambicję odsłaniać i charakteryzować tendencje zaznaczające się w najnowszej polskiej fantastyce. Na uwagę zasługuje zjawisko zacierania czy „zamazywania” przez pisarzy granic między światem zbudowanym na realnych podstawach a kreacją fantastyczną. Równie interesujący i godny odnotowania jest fakt, że polscy autorzy – mimo przewagi tekstów fantasy i ich ogromnej popularności – wciąż jeszcze sięgają po gatunek science fiction czy hard science fiction. Jaka zatem przyszłość rysuje się przed polską literaturą fantastyczną? Odpowiedź nie jest prosta i jednoznaczna, dlatego powstała niniejsza książka, do lektury której serdecznie zapraszam.	google_books
9788090947603	Historia zamku Špilberk, Muzeum Miejskie w Brnie	Michal Hančák	iPublishing, spol. s r. o.	2025-03-30	http://books.google.com/books/content?id=o4NREQAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Czy wiesz, że ten zamek był niegdyś najbardziej przerażającym więzieniem w całej monarchii Austro-Węgierskiej? Znasz słynnych więźniów, których historie wciąż przyciągają turystów z całej Europy Środkowej? Posłuchaj opowieści o zamku Špilberk i poznaj losy tych, którzy odcisnęli na nim swoje piętno. Zamek, twierdza, owiane złą sławą więzienie i koszary wojskowe – Špilberk był świadkiem wystawnych uczt i tragicznych losów, stając się symbolem zarówno władzy, jak i cierpienia. Przeszedł dramatyczne zmiany, o których większość odwiedzających nie ma pojęcia. Dzięki naszemu przewodnikowi audiowizualnemu możesz teraz usłyszeć tę historię tam, gdzie się naprawdę wydarzyła.	google_books
9788382101928	Valentino Rossi. Biografia	Stuart Barker	Wydawnictwo SQN	2021-05-27	http://books.google.com/books/content?id=LE0wEAAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	„Stuart Barker pisze tak, jak Valentino Rossi jeździ (…). Lektura obowiązkowa dla wszystkich fanów motocykli” „Daily Mirror” Valentino Rossi to symbol odwagi, ryzyka i śmiałości. Współczesny gladiator, który ryzykuje życiem za każdym razem, gdy wskakuje na swoją maszynę, by walczyć o zwycięstwo w najbardziej niebezpiecznych wyścigach na świecie. To też wieczny optymista i charyzmatyczny lekkoduch, który triumfy na torze potrafi świętować, pokonując rundę honorową w towarzystwie… kurczaka ludzkich rozmiarów. Jak doszedł do niewyobrażalnej sławy i rozkochał w sobie fanów? Dlaczego zachwycają się nim największe gwiazdy Hollywood, takie jak Brad Pitt czy Tom Cruise? Czemu tak bardzo nie lubi Maxa Biaggiego, a Sete Gibernau z dobrego znajomego stał się wielkim wrogiem włoskiego mistrza? W jakie afery wplątał się Rossi przez pieniądze? To książka naszpikowana anegdotami i historiami z życia legendy wyścigów motocyklowych, człowieka, który poznał smak niewyobrażalnej popularności i bajecznego bogactwa, był świadkiem śmiertelnych wypadków z udziałem rywali i przyjaciół, odniósł poważne obrażenia i stoczył najbardziej pamiętne batalie w cyklu MotoGP – zarówno na torze, jak i poza nim. Stuart Barker wykorzystał wypowiedzi Rossiego oraz niepublikowane wcześniej rozmowy z tymi, którzy są częścią historii Vale od samego początku. Napisał porywającą i pełną adrenaliny biografię chłopaka z Tavullii, który spełnił swoje marzenia o chwale.	google_books
9788382300987	Blizna. Wstrząsająca biografia lidera zespołu Red Hot Chili Peppers	Anthony Kiedis, Larry Sloman	Sonia Draga Sp. z o.o.	2021-02-16	http://books.google.com/books/content?id=bmweEAAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Młodzieńcze lata Anthony’ego Kiedisa, lidera jednego z najpopularniejszych zespołów rockowych na świecie, są doskonałym materiałem na książkę. Blizna to wspomnienie tamtych szalonych lat wypełnionych muzyką, seksem, narkotykami i imprezami. To opowieść o pogoni za silnymi wrażeniami, o życiu na krawędzi i o poszukiwaniu upustu dla posiadanych zasobów energii. Bez zbędnego koloryzowania, bez taniego ubarwiania rzeczywistości, za to z odpowiednią dozą szczerości powstała biografia człowieka, którego muzyka i ogromna pasja zaprowadziły na szczyty sławy. Oto moja relacja z tamtych czasów, a także historia o tym, jak chłopak, który urodził się w Grand Rapids w stanie Michigan, przeniósł się do Hollywood i na końcu tęczy znalazł więcej, niż mógł udźwignąć. Oto moja historia, wszystkie blizny i cała reszta. Anthony Kiedis „Czytając tę przejmującą historię, uświadamiamy sobie, jak niewiele wiemy o artystach, których oglądamy na wystylizowanych teledyskach i podczas koncertów. Blizna to gratka dla wszystkich fanów RHCP (…) – pokazuje bez żadnego upiększania zwariowany hollywoodzki światek undergroundowych klubów, narkotykowych dilerów oraz mniejszych, a wraz z upływem czasu i rosnącą popularnością RCCP, coraz większych gwiazd, które przewinęły się przez życie Kiedisa”. Gazeta Studencka „Kopalnia pikantnych ciekawostek o Cher, Madonnie czy Sylwestrze Stallone. Fani Papryczek odnajdą tu sporo zakulisowych wieści o powstaniu kapeli i słynnych balangach do upadłego”. Marie Claire	google_books
9788324040421	Ksiądz Paradoks. Biografia Jana Twardowskiego	Magdalena Grzebałkowska	Otwarte	2020-03-30	http://books.google.com/books/content?id=2Lk9DwAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Głośny debiut Magdaleny Grzebałkowskiej. Bestsellerowa biografia „księdza od biedronek”. Wszyscy znamy księdza Jana Twardowskiego, ale niewiele o nim wiemy. Jaki był naprawdę? Autorka dotarła do nieznanych zapisków księdza Jana. Dzięki nim poznajemy człowieka pełnego sprzeczności. Dlaczego czuł się samotny? Skąd brała się u niego wielka potrzeba przyjaźni z kobietami? Czy wieloletnie kontakty z oficerem SB są rzeczywiście rysą na jego wizerunku? „Ksiądz Paradoks” to niezwykła historia człowieka, który wymyka się wszelkim schematom. Poznaj jego młodość, początki niezwykłej popularności oraz ostatnie, najbardziej tajemnicze lata jego życia.	google_books
9788324062058	Niewygodny prorok. Biografia ks. Jana Ziei	Jacek Moskwa	Otwarte	2020-12-07	http://books.google.com/books/content?id=z11xEAAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Gdy chodzi o dobro bliźniego, nie ma miejsca na kompromisy Ksiądz Jan Zieja – świadek XX wieku, który całym życiem służył Bogu i człowiekowi. Podczas doświadczeń kampanii w 1920 roku z przykazania „Nie zabijaj!” uczynił swoje credo. W ciężkich czasach był zawsze blisko tych, którzy go potrzebowali – w trakcie drugiej wojny światowej pełnił funkcję naczelnego kapelana Szarych Szeregów, Batalionów Chłopskich oraz Batalionu „Baszta” w Powstaniu Warszawskim. Natchniony prorok i charyzmatyczny kaznodzieja – asystował przy pierwszych zakonnych ślubach świętej Faustyny Kowalskiej i przyjął konspiracyjną przysięgę Witolda Pileckiego, a także prowadził rekolekcje, w których uczestniczył biskup Karol Wojtyła. Choć przyjaźnił się ze Stefanem Wyszyńskim, w zasadniczych sprawach potrafił przeciwstawić się nawet jemu. Zawsze w wirze zmian, został jednym z pierwszych członków Komitetu Obrony Robotników. Duszpasterz napędzany ewangelicznym przykazaniem miłości. Apostoł Kościoła ubogiego, sam nigdy nie przyjmował pieniędzy za posługi religijne. Książka Niewygodny prorok powstała na podstawie szerokich badań archiwalnych, świadectw współczesnych, a także rozmów z samym bohaterem. To lektura krzepiąca, po raz pierwszy w sposób pełny prezentująca życie księdza Jana Ziei. Jacek Moskwa – dziennikarz, pisarz, wieloletni korespondent polskich mediów w Watykanie. Autor m.in. wielokrotnie wznawianego wywiadu rzeki z księdzem Janem Zieją Życie Ewangelią, Tajemnic konklawe 1978 oraz czterotomowej biografii Droga Karola Wojtyły. Powyższy opis pochodzi od wydawcy.	google_books
9788382109795	Johan Cruyff. Biografia totalna	Auke Kok	Wydawnictwo SQN	2024-06-19	http://books.google.com/books/content?id=0e0OEQAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Kłótliwy, błyskotliwy, arogancki, wizjonerski. Johan Cruyff był jednym z największych piłkarzy wszech czasów, światowym fenomenem i prawdopodobnie najsłynniejszym Holendrem XX wieku. Zmieniał sposób gry, zarówno gdy biegał po boisku, jak i wtedy gdy siedział na ławce trenerskiej. Krzewił futbol totalny i pozostawił po sobie trwałe dziedzictwo. Chociaż Cruyff prowadził znaczną część swojej wspaniałej kariery i życia w świetle reflektorów, pod wieloma względami jako człowiek i sportowiec wciąż pozostaje całkowitą tajemnicą. Ta biografia, oparta na latach szeroko zakrojonych badań, jako pierwsza obejmuje wszystkie aspekty jego życia i pracy, od wpływu, jaki wywarł na wielkie drużyny Ajaxu i Holandii w latach 70., po rolę, którą odgrywał w tworzeniu nowoczesnego fenomenu piłkarskiego, jakim jest FC Barcelona. Opierając się na setkach wywiadów z przyjaciółmi z dzieciństwa i szkoły, trenerami, kolegami z drużyny, przeciwnikami z boiska, współpracownikami biznesowymi i członkami rodziny legendy futbolu, Auke Kok napisał biografię totalną. Historię chudego, zuchwałego piłkarza z ulicy, który stał się genialnym graczem, inspirującym menedżerem oraz piłkarskim pionierem i filozofem. Oto, kim był Johan Cruyff.	google_books
9788324061518	Kołakowski. Czytanie świata. Biografia	Zbigniew Mentzel	Otwarte	2020-10-05	http://books.google.com/books/content?id=A2FxEAAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Pierwsza pełna biografia geniusza, który uczył Polaków filozofii Imponujący wiedzą mistrz. Nauczyciel, jakiego każdy chciałby dziś mieć Leszek Kołakowski, wybitny filozof i autorytet niechętnie mówiący o życiu prywatnym. Znawca chrześcijaństwa i filozofii religii do końca życia pozostający poza Kościołem. Pierwszy laureat amerykańskiej Nagrody im. Johna Klugego nazywanej filozoficznym Noblem. Pozbawiony w PRL-u prawa nauczania opuścił w 1968 roku Polskę, by wkrótce zostać profesorem prestiżowego All Souls College w Oxfordzie. Po jego śmierci Zbigniew Mentzel dotarł do bogatych archiwów udostępnionych przez rodzinę. Dzięki temu mógł opowiedzieć historię fascynującego człowieka, którego przenikliwości bał się Gomułka i partyjni towarzysze. Napisane przez Kołakowskiego Tezy o nadziei i beznadziejności w latach 70. stały się głównym źródłem intelektualnej inspiracji dla rodzącej się w Polsce opozycji demokratycznej, a Główne nurty marksizmu pozostają jedną z najważniejszych książek XX wieku. W bestsellerowych popularyzatorskich Mini wykładach o maxi sprawach i O co nas pytają wielcy filozofowie? przybliżył milionom Polaków dorobek najwybitniejszych myślicieli w historii. Zbigniew Mentzel – pisarz, krytyk, felietonista. Przygotował do druku osiem tomów pism rozproszonych Leszka Kołakowskiego. Autor zbioru rozmów z filozofem zatytułowanych Czas ciekawy, czas niespokojny oraz kilku zbiorów opowiadań i felietonów, a także powieści Wszystkie językiświata i Spadający nóż.	google_books
9788324062713	Kamala Harris. Pierwsza biografia	Mieczysław Godyń, Aleksandra Gietka-Ostrowska, Dan Morain, Dominika Chylińska, Filip Godyń	Otwarte	2021-02-18	http://books.google.com/books/content?id=sWFxEAAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Na tworzącą się historię patrzyła z dziecięcego wózka, gdy rodzice zabierali ją ze sobą na protesty, które zmieniły Amerykę. Córka imigrantów, dorastająca w różnorodnej, słonecznej Kalifornii, szybko odczuła, czym są nierówne szanse. Największą inspiracją jest dla niej mama - Shyamala, która zawsze powtarzała córce: Możesz być pierwsza, ale pamiętaj, byś nie była ostatnia. Ona sama mówi, że gdy światła polityki gasną, ze wszystkich ról, jakie odgrywa w życiu: prokuratorki, polityczki, wiceprezydentki USA, najważniejsze jest dla niej bycie Momalą – matką swoich przybranych dzieci. Choć jej ciepły uśmiech znają wszyscy, w swojej karierze Kamala niejednokrotnie dała się poznać jako twarda, zdecydowana negocjatorka. Jako prokuratorka zawsze stawała po stronie ofiar. Stanowczo potępiła działania policji po śmierci George’a Floyda. Dziś jest symbolem nadziei na koniec rządów populistów na całym świecie. Niezwykła historia dziewczyny z Kalifornii, o hindusko-jamajskich korzeniach, która stała się najważniejszą kobietą w Ameryce, to także intrygująca opowieść o tym wielokulturowym, pełnym sprzeczności i niezmiennie fascynującym kraju. Dan Morain – dziennikarz, od czterech dekad zajmuje się polityką Stanów Zjednoczonych. Przez ponad dwadzieścia lat pracował dla „Los Angeles Times”.	google_books
9788380539693	Harry Styles. Nieoficjalna biografia	Danny White	Wydawnictwo Kobiece	2023-06-27	http://books.google.com/books/content?id=YLXHEAAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Zyskał rozgłos jako członek zespołu One Direction, ale smak sławy poznał jako jeden z najpopularniejszych solowych piosenkarzy na świecie, aktor hollywoodzki i ikona mody. Prześledź losy Harry’ego od dzieciństwa aż po szczyt popularności. Po rozpadzie One Direction od nowa budował artystyczny wizerunek. Nie poprzestał jednak na branży muzycznej. Pasja i talent zaprowadziły go na plan kinowego przeboju Dunkierka oraz do programu rozrywkowego Saturday Night Live. Stał się także ikoną mody i ambasadorem legendarnej marki Gucci. To on przejdzie do historii jako pierwszy mężczyzna, który pojawił się na okładce amerykańskiej edycji „Vogue’a”. Harry Styles jest uosobieniem wszechstronnej i nowoczesnej gwiazdy pop. I nie powiedział jeszcze ostatniego słowa… To pozycja obowiązkowa dla każdego fana rozlicznych talentów Harry’ego Stylesa. Harry: ‒ tworzy niepowtarzalną muzykę ‒ album Fine Line zdobył wielkie uznanie na całym świecie: „Dzieło artysty świadomego swojego talentu” („Guardian”), „Błyskotliwa i odważna płyta” („Independent”), „Czysta radość” („NME”). ‒ łączy pokolenia – jego wielbiciele dojrzewają razem ze swoim idolem, rzesze wiernych słuchaczy towarzyszą mu od czasów One Direction, powiększając się wciąż o nowych fanów. ‒ urzeka naturalnością, charyzmą i wyrafinowaniem – jego profile w mediach społecznościowych śledzi ogromna liczba fanów – ma ok. 38 milionów obserwujących na Instagramie, 36 milionów na Twitterze, 16 milionów na Facebooku. Daphne Bugler w magazynie „GQ” stwierdziła, że „świat nie zasługuje na Harry’ego Stylesa”. Ale świat ma Harry’ego Stylesa. Oto jego historia.	google_books
9788379241132	The Beatles. Jedyna autoryzowana biografia. Wydanie II	Hunter Davies	Wydawnictwo SQN	2019-07-21	http://books.google.com/books/content?id=0PWkDwAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Jedyna autoryzowana biografia. Jest tylko jedna książka prawdziwie opisująca Beatlesów. Właśnie trzymasz ją w dłoni. W latach 1967–1968 Hunter Davies spędził osiemnaście miesięcy z Beatlesami, którzy wówczas definiowali gusta nowej generacji i tworzyli podstawy współczesnej muzyki popularnej. Jako ich jedyny autoryzowany biograf miał nieograniczony dostęp nie tylko do Johna, Paula, George’a i Ringo, ale również do ich przyjaciół, rodzin i znajomych. Podczas współpracy z zespołem i jego otoczeniem zebrał pokaźne bogactwo materiałów – często intymnych i odsłaniających nieznane fakty. To czyni z niniejszej książki biografię-matkę, na której pozostali biografowie opierają swoje własne teksty. The Beatles to rzetelne i kompletne dzieło, które aktualizuje historię członków zespołu o informacje na temat ich solowych karier i życia prywatnego. Dzięki archiwaliom autora i samych Beatlesów książka ta rzuca zupełnie nowe światło na legendę gigantów rock and rolla. Opieka merytoryczna: Piotr Metz.	google_books
9788394479534	Niech liczy się tylko Jesús: Ilustrowana biografia św. Josemaríi Escrivy założyciela Opus Dei	Jesús Gil, Enrique Muñiz	Biuro Informacyjne Opus Dei w Polsce	2020-06-22	http://books.google.com/books/content?id=ZZzsDwAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Niech liczy się tylko Jezus to biografia założyciela Opus Dei. Zawiera ponad 300 zdjęć, map, infografik i reprodukcji odręcznych notatek. Autorzy książki – Jesús Gil i Enrique Muñiz – ufają, że "ilustracje pomogą czytelnikom nie tylko zrozumieć życie św. Josemaríi, ale wprowadzą ich także w atmosferę poszczególnych wydarzeń".	google_books
9788381296786	Roger Federer. Biografia	Roger Federer	Wydawnictwo SQN	2021-09-12	http://books.google.com/books/content?id=nUlDEAAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Zajrzyj za kulisy życia i kariery tenisowego geniusza! W wieku, w którym większość tenisistów już od dawna jest na sportowej emeryturze, Roger Federer zgotował swoim fanom comeback rodem z hollywoodzkich filmów. Szwajcar, jedna z najwybitniejszych postaci współczesnego sportu, pokazuje, że nie istnieją dla niego absolutnie żadne ograniczenia. Rene Stauffer dzięki wyjątkowo bliskim relacjom z tenisistą burzy „czwartą ścianę” i pokazuje jego ludzką twarz. Z biografii wyłania się obraz człowieka, który z trudnego dziecka, karnie pielącego po swoich kolejnych wybuchach furii ogródek stał się oazą spokoju. Zaangażowanego w pomoc innym do tego stopnia, że peany na jego cześć pisze sam Bill Gates. Obraz perfekcjonisty, podczas tenisowych turniejów pracującego jak… szwajcarski zegarek. Co ukształtowało tenisowego giganta? Jaki wpływ na rozwój jego talentu mieli rodzice? Jak radzi sobie z presją sukcesu, która towarzyszy mu od wielu lat? A wreszcie: jak to możliwe, że mimo niebotycznych sukcesów pozostaje gościem, z którym chciałbyś wyskoczyć po pracy na piwo? Poznajcie historię Rogera Federera opowiedzianą tak dogłębnie i ujmująco jak nigdy dotąd.	google_books
9788379246199	Cristiano Ronaldo. Biografia.	Guillem Balagué	Wydawnictwo SQN	2019-07-04	http://books.google.com/books/content?id=xcakDwAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Poznaj prawdziwą historię jednego z najlepszych piłkarzy w historii futbolu! Może się wydawać, że o Cristiano Ronaldo powiedziano i napisano już wszystko. Na ile jednak znany kibicom wizerunek piłkarza jest zgodny z prawdą? Ta książka pokazuje, jak złożoną osobowością jest Portugalczyk. I jak niewiele wiedzieli o nim dotychczas nawet jego najwierniejsi fani. W tej biografii nie znajdziecie wielu statystyk, opisów meczów i akcji CR7. Dowiecie się za to, że już w wieku 14 lat wymykał się nocami do siłowni, niewiele brakowało, by zakontraktowała go FC Barcelona, a gdy już jako nastolatek oglądał mecz Realu w telewizji, powiedział kolegom: „Kiedyś będę tam grał”. W najnowszym wydaniu dodatkowo przekonacie się, jak to się stało, że zdecydował się opuścić Królewskich i trafił do Juventusu. Guillem Balagué wybrał się na Maderę, do Lizbony, Manchesteru, Madrytu. Odwiedził dziesiątki miejsc, rozmawiał z setkami osób, poszukując odpowiedzi na jedno pytanie: kim jest Cristiano Ronaldo? Piłkarz nie chciał, by ta książka się ukazała. Właśnie dlatego, że jest szczera, obiektywna, PRAWDZIWA. A przez to najlepsza, jaka dotychczas o Ronaldo powstała. Piłkarska Książka Roku w Wielkiej Brytanii – „Cross Sports Book Awards”. Piłkarska Książka Roku w Polsce – „Sportowa Książka Roku”.	google_books
9788383307275	Tupac Shakur. Autoryzowana biografia	Staci Robinson	Wydawnictwo SQN	2025-06-04	http://books.google.com/books/content?id=ftVhEQAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Artysta, poeta, aktor, rewolucjonista, legenda – po prostu Tupac Shakur. Jedyna autoryzowana biografia Tupaca Shakura, która powstała z inicjatywy jego matki – Afeni Shakur. To historia człowieka, który stał się symbolem sprzeciwu, głosem pokolenia i jedną z największych ikon kultury XX wieku. Tupac był kimś więcej niż raperem. Był poetą, aktywistą, marzycielem wychowanym przez Czarną Panterę. Jego życie to podróż od harlemskich ulic po czerwone dywany, od więziennych cel po protesty, od miłości po gniew. Znał brutalność systemu, ale też jego piękno – bo z betonu potrafił wyrastać jak róża. Autorka, Staci Robinson, znała Tupaca osobiście. Spędziła lata na rozmowach z jego rodziną, przyjaciółmi, nauczycielami. Zbudowała zaufanie, dzięki któremu poznajemy Tupaca takim, jakim był naprawdę – wrażliwym chłopakiem z notatnikiem, wojownikiem z misją, artystą rozdartym między światami. Ta książka to nie tylko opowieść o życiu Tupaca. To głos tych, którzy byli obok – od jego pierwszych wersów aż po ostatnie słowa.	google_books
9788324034413	Elon Musk. Biografia twórcy PayPala, Tesli, SpaceX	Ashlee Vance	Otwarte	2020-03-30	http://books.google.com/books/content?id=erg9DwAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	BESTSELLEROWA BIOGRAFIA CZŁOWIEKA, KTÓRY ZMIENIA ŚWIAT NA NASZYCH OCZACH Steve Jobs chciał waszych pieniędzy. Mark Zuckerberg pragnie wam pomóc udostępnić zdjęcia bobasów. Elon Musk zamierza uratować świat przed zagładą. Wizjoner, geniusz, nieznośny szef, najbardziej zuchwały przedsiębiorca Doliny Krzemowej, jeden z najbogatszych ludzi na ziemi. Człowiek stawiany w jednym szeregu z Thomasem Edisonem, Henrym Fordem i Stevem Jobsem. Każdy start-up w jego rękach zmienia się w złoto. Stworzył PayPala, koncern samochodowy Tesla Motors, a także SpaceX – firmę wysyłającą prywatne rakiety w kosmos. Muskowi udało się, mimo że jego życie jest niedorzeczne. A może właśnie dlatego. Żeby przekonać rząd, że pojawił się nowy gracz w wyścigu kosmicznym, zaparkował rakietę na trawniku przed siedzibą Federalnej Administracji Lotnictwa w Waszyngtonie. Gdy po auta Tesli ustawiały się kolejki chętnych, Leonardo DiCaprio błagał Elona o egzemplarz elektrycznego Roadstera. Musk oczywiście odmówił. Ashlee Vance, publicysta specjalizujący się w nowoczesnych technologiach, przeprowadził dziesiątki wywiadów z rodziną, przyjaciółmi i pracownikami Elona Muska. Dotarł także do jego wrogów. Sam Musk przyrzekł, że zrobi wszystko, by nie dopuścić do publikacji tej książki. Nagle zmienił zdanie – oto ona.	google_books
9788328098305	Colette. Biografia	Claude Francis, Fernande Gontier	WAB	2022-04-12	http://books.google.com/books/content?id=O4MSEQAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Gdyby Sidonie-Gabrielle Colette urodziła się sto lat później, niż to rzeczywiście miało miejsce, bez wątpienia przyćmiłaby wszystkie bohaterki kronik towarzyskich i kolorowej prasy. Skandal wydawał się jej sposobem na życie, odsuwał w cień jej literaturę. Starała się wychodzić poza reguły, przekraczać utarte wzorce zachowań. Liczne „przyjaźnie” homo- i heteroseksualne oraz na poły kazirodczy związek z pasierbem wydobyły Colette z uwierającego ją gorsetu stereotypów. Próbowała spełniać się w najróżniejszych rolach: pisarki, aktorki, tancerki, mima, dziennikarki i krytyczki teatralnej, ale też żony i matki. Claude Francis i Fernande Gontier podjęły próbę wskazania tego, co w jej życiu należy do legendy i tego, co naprawdę się wydarzyło. Z ich książki wyłania się postać dużo bardziej dwuznaczna, bardziej złożona, bardziej amoralna i z pewnością bardziej utalentowana niż ta, która stała się bohaterką legendy.	google_books
9788324086689	Avicii. Biografia Tima Berglinga	Mosesson Mans	Otwarte	2022-04-15	http://books.google.com/books/content?id=e3txEAAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Intymna biografia kultowego DJ-a, który odszedł zbyt wcześnie. Avicii był wizjonerem. Poprzez swoje muzyczne wyczucie i unikatowy styl zdefiniował epokę, w której szwedzka i europejska muzyka house zawładnęła światem. Ale Tim Bergling był również introwertycznym młodym człowiekiem zmuszonym do dorastania w nieludzko szybkim tempie. Po serii nagłych wypadków i pobytów w szpitalu latem 2016 roku przestał koncertować. Zaledwie dwa lata później świat obiegła szokująca informacja – jeden z najsławniejszych na świecie DJ-ów popełnił samobójstwo w hotelowym pokoju w Omanie. Pozostawił po sobie największe hity klubowej sceny, takie jak Wake Me Up, Waiting for Love czy Levels, i gigantyczną fortunę. Jego utwory mają miliardy odtworzeń w serwisach streamingowych. Avicii. Biografia Tima Berglinga została napisana przez wielokrotnie nagradzanego dziennikarza Månsa Mosessona, który dzięki wywiadom z rodziną Tima, jego przyjaciółmi i kolegami z branży muzycznej dogłębnie poznał producenta-gwiazdę. Książka przedstawia szczery obraz Tima i jego życiowych poszukiwań. Autor nie stronił od ukazywania demonów, z którymi walczył chłopak, i propozycji odpowiedzi na najtrudniejsze pytania dotyczące losów jednej z najjaśniej świecących gwiazd muzycznych ostatniej dekady.	google_books
9788324063529	Wiek paradoksów. Czy technologia nas ocali?	Natalia Hatalska	Otwarte	2021-08-16	http://books.google.com/books/content?id=315xEAAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Dlaczego płacimy za oszukiwanie samych siebie? Czy robot może emocjonalnie złamać człowieka? Jak wielkie firmy wykorzystują naszą samotność? Natalia Hatalska pozwala inaczej niż dotychczas spojrzeć na to, czym jest życie w XXI wieku, odkryć i zrozumieć mechanizmy kierujące relacjami, technologią i polityką. Jej książka zmusza do tego, byśmy się zatrzymali i zadali sobie najważniejsze pytania: Czy można powstrzymać rozwój technologii? Co nas czeka, gdy inżynieria genetyczna pozwoli na hodowanie ludzi na szeroką skalę? Gdzie jest granica postępu technologicznego, o ile w ogóle taka granica istnieje? To ostatni moment na zadanie niektórych z tych pytań i szukanie na nie odpowiedzi. Natalia Hatalska mówi o najważniejszych problemach współczesnego świata: o samotności, manipulacji, dezinformacji, a także o technologii, która może przejąć nad nami kontrolę. Nie daje gotowych odpowiedzi, lecz poszerza perspektywę. Prowokuje do tego, byśmy gruntownie przemyśleli nasz stosunek do rzeczywistości XXI wieku. Natalia Hatalska – analityczka trendów, publicystka, założycielka i prezeska instytutu badań nad przyszłością infuture.institute. Zaliczana do dziesięciu najważniejszych autorytetów polskiego biznesu. Nagrodzona tytułem Digital Shaper w kategorii wizjoner – przyznawanym osobom, które mają ponadprzeciętny wkład w rozwój gospodarki cyfrowej w Polsce. „Financial Times” umieścił ją na liście New Europe 100 – stu osób z Europy Środkowo-Wschodniej, które zmieniają społeczeństwo, politykę i biznes, prezentując nowe podejście do dominujących problemów.	google_books
9788323135999	Camino Polaco. Teologia - Sztuka - Historia - Teraźniejszość. Tom 3	Piotr Roszak, Waldemar Rozynkowski	Wydawnictwo Naukowe Uniwersytetu Mikołaja Kopernika	2014	http://books.google.com/books/content?id=h4c9DwAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Oddajemy do rąk Państwa tom trzeci wydawnictwa zbiorowego Camino Polaco. Teologia – sztuka – historia – teraźniejszość. Powstał on jako owoc współpracy oraz interdyscyplinarnych badań nad fenomenem Dróg św. Jakuba w Polsce oraz w Europie. Część tekstów zamieszczonych w książce została wygłoszona jako referaty podczas konferencji naukowej zorganizowanej w dniach 29–30 maja 2015 roku w Centrum Dialogu im. Jana Pawła II w Toruniu. Większość artykułów powstała jednak jako pokłosie zainteresowań różnych osób zarówno postacią św. Jakuba, jak i dynamicznie rozwijającego się zjawiska pielgrzymowania drogami naznaczonymi obecnością Apostoła. Od początku tworzenia wydawnictwa Camino Polaco towarzyszy nam doświadczenie współpracy z różnymi środowiskami zarówno w Polsce, jak i z zagranicą. Szczególnie bliskie, a przede wszystkim ważne z punktu widzenia badań nad fenomenem Dróg św. Jakuba stają się kontakty z wieloma osobami i środowiskami z Hiszpanii. W tym miejscu pragniemy podziękować wszystkim autorom tekstów, którzy odpowiedzieli na nasze zaproszenie. W prezentowanym tomie dominują teksty historyków. Ich obfita obecność wskazuje wyraźnie na to, jak wiele kwestii z dziejów kultu św. Jakuba oczekuje na zainteresowanie i opracowanie. W prezentowanym tomie nie brakuje jednak rozpraw teologów, filozofów, archeologa czy historyka sztuki. Podobnie jak w tomie pierwszym i drugim Camino Polaco, także i w tym znajdujemy artykuły, które pozostają wierne metodologii właściwej dla konkretnej dyscypliny nauki. Pod względem treści stawiają one sobie za cel zarówno podjęcie nowych szczegółowych badań, ukazanie na wybranych przykładach aktualnego stanu badań, jak i w kilku przypadkach ukazania różnych kierunków refleksji nad Camino. Zawsze pojawiają się nowe kwestie, do tej pory niepodejmowane. Dla przykładu z tekstów badaczy hiszpańskich interesujący jest artykuł ks. Alejandro Barrala poświęcony wynikom badań archeologicznych w Santiago de Compostela.Oddajemy do rąk Państwa tom trzeci wydawnictwa zbiorowego Camino Polaco. Teologia – sztuka – historia – teraźniejszość. Powstał on jako owoc współpracy oraz interdyscyplinarnych badań nad fenomenem Dróg św. Jakuba w Polsce oraz w Europie. Część tekstów zamieszczonych w książce została wygłoszona jako referaty podczas konferencji naukowej zorganizowanej w dniach 29–30 maja 2015 roku w Centrum Dialogu im. Jana Pawła II w Toruniu. Większość artykułów powstała jednak jako pokłosie zainteresowań różnych osób zarówno postacią św. Jakuba, jak i dynamicznie rozwijającego się zjawiska pielgrzymowania drogami naznaczonymi obecnością Apostoła. Od początku tworzenia wydawnictwa Camino Polaco towarzyszy nam doświadczenie współpracy z różnymi środowiskami zarówno w Polsce, jak i z zagranicą. Szczególnie bliskie, a przede wszystkim ważne z punktu widzenia badań nad fenomenem Dróg św. Jakuba stają się kontakty z wieloma osobami i środowiskami z Hiszpanii. W tym miejscu pragniemy podziękować wszystkim autorom tekstów, którzy odpowiedzieli na nasze zaproszenie. W prezentowanym tomie dominują teksty historyków. Ich obfita obecność wskazuje wyraźnie na to, jak wiele kwestii z dziejów kultu św. Jakuba oczekuje na zainteresowanie i opracowanie. W prezentowanym tomie nie brakuje jednak rozpraw teologów, filozofów, archeologa czy historyka sztuki. Podobnie jak w tomie pierwszym i drugim Camino Polaco, także i w tym znajdujemy artykuły, które pozostają wierne metodologii właściwej dla konkretnej dyscypliny nauki. Pod względem treści stawiają one sobie za cel zarówno podjęcie nowych szczegółowych badań, ukazanie na wybranych przykładach aktualnego stanu badań, jak i w kilku przypadkach ukazania różnych kierunków refleksji nad Camino. Zawsze pojawiają się nowe kwestie, do tej pory niepodejmowane. Dla przykładu z tekstów badaczy hiszpańskich interesujący jest artykuł ks. Alejandro Barrala poświęcony wynikom badań archeologicznych w Santiago de Compostela.	google_books
9788323133483	Studia nad nauką i technologią. Wybór tekstów	Ewa Bińczyk, Aleksandra Derra 	Wydawnictwo Naukowe Uniwersytetu Mikołaja Kopernika	2014	http://books.google.com/books/content?id=OU0mDwAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Studia nad nauką i technologią (Science and Technology Studies, STS) to interdyscyplinarna, wielowątkowa, rozbudowana, prężnie rozwijająca się współcześnie dziedzina nauki. W prezentowanym zbiorze znajdują się zarówno klasyczne teksty z tego obszaru, jak i najnowsze opracowania, poruszające niezwykle bogatą problematykę, z zaskakującymi naukowo rozwiązaniami. Prezentowane nurty to: psychosocjologia poznania naukowego Ludwika Flecka, nowy eksperymentalizm Iana Hackinga, amodernistyczny konstruktywizm Donny Haraway, teoria aktora-sieci Brunona Latoura, Michela Callona i Johna Lawa, etnografia laboratorium Karin Knorr-Cetiny, pragmatyczny realizm Andrew Pickeringa, badania kontrowersji naukowych Harry’ego Collinsa, historia nauki Stevena Shapina oraz feministyczne analizy nauk biologicznych Ruth Hubbard. Badania autorek i autorów przedstawionej antologii cechuje rzadka umiejętność łączenia fascynującego materiału empirycznego z oryginalnymi, wysokiej jakości interpretacjami o charakterze teoretycznym, wzbogacone wyrafinowaną, konsekwentnie prowadzoną argumentacją filozoficzną. Znajdziemy tutaj ogromne bogactwo heterogenicznych pierwszoplanowych i drugoplanowych aktorów. Są nimi między innymi: odczyn Wassermanna, statystyka, niejednoznaczne choroby psychiczne, wojny o naukę, lis przechera, technologie wizualizacji, wąglik Pasteura, komórki mikrogleju, podmiotowość jako sieć, rzeka Missisipi, konsumpcja, przegrzebki i rybacy znad zatoki Sait-Brieue, efekt placebo, DNA, dietetyka czy przepis na filozoficznego kurczaka. Zapraszamy do fascynującej lektury na temat nauki, technologii i zbiorowości, które wspólnie zamieszkują współczesny świat.	google_books
9788382309881	Bóg, nauka, dowody.	Michel-Yves Bolloré, Olivier Bonnassies	Sonia Draga Sp. z o.o.	2025-04-28	http://books.google.com/books/content?id=e9VZEQAAQBAJ&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api	Zaproszenie do refleksji i dialogu między nauką a religią. Przez blisko cztery wieki, od Kopernika przez Galileusza i Darwina do Freuda, dokonywano coraz to nowych spektakularnych odkryć naukowych, dzięki którym stwarzano wrażenie, że można objaśnić Wszechświat, nie uciekając się do działania jakiegoś kreatora. Tym sposobem w początkach XX wieku w sferze idei zatriumfował materializm. Ale późniejsze badania podważyły to, co dotąd powszechnie uważano za pewne, można więc dzisiaj powiedzieć, że materializm, który zawsze był wiarą taką samą jak inne, staje się wiarą irracjonalną. Autorzy przystępnie przedstawiają pasjonującą historię odkryć naukowych i przegląd niepodważonych nowych dowodów na istnienie Boga. Stawiają też pytanie: skoro na początku ubiegłego wieku wiara w Boga zdawała się kłócić z nauką, czy dzisiaj nie jest przeciwnie?	google_books
\.


--
-- Data for Name: book_item; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.book_item (id, isbn, is_available, current_location, created_at) FROM stdin;
2233dfb0-6ca2-4cd3-bc77-a657109f98c4	9788323396949	t	library	2025-11-12 14:38:04.878047+00
e23da12b-80db-4bf4-b1b6-8f3f972f38e5	9788323396949	t	library	2025-11-12 14:38:04.878047+00
da9e6cc5-2afc-4456-a891-3f1464e77b9b	9788323396949	t	library	2025-11-12 14:38:04.878047+00
602ac730-2b38-4578-ade6-10c6fe4b3fa1	9788323396949	t	library	2025-11-12 14:38:04.878047+00
c5c7224c-1ede-4b60-af54-99d20f1bf1ac	9788323396949	t	library	2025-11-12 14:38:04.878047+00
68fa60cd-a515-40d2-b792-084b116ecc75	9788323396949	t	library	2025-11-12 14:38:04.878047+00
6f31bd17-d50b-4c29-8e20-20647b9ab452	9788323396949	t	library	2025-11-12 14:38:04.878047+00
967caa04-879d-48f6-96b4-18c1fd6b06a5	9788323396949	t	library	2025-11-12 14:38:04.878047+00
b1703ffc-fc31-4d69-ba53-d3bad18b9a0d	9788323396949	t	library	2025-11-12 14:38:04.878047+00
09e83e86-3045-463e-aa09-885302c793ad	9788377012086	t	library	2025-11-12 14:38:04.878047+00
cc1b65b7-1da7-4baa-a5c4-5bf8d111e402	9788377012086	t	library	2025-11-12 14:38:04.878047+00
eaee15e2-09e0-4eda-b4e4-9242db70cde9	9788377012086	t	library	2025-11-12 14:38:04.878047+00
ab0afbb4-3d95-40b5-ba8e-9e3bec2b6f45	9788377012086	t	library	2025-11-12 14:38:04.878047+00
29cc8f63-9551-4ceb-a5a0-91e495ee6e35	9788377012086	t	library	2025-11-12 14:38:04.878047+00
b018c991-7a02-4299-9352-c7ae706297f5	9788377012086	t	library	2025-11-12 14:38:04.878047+00
d4be4c53-6394-4028-b1f3-a755fd822bb0	9788377012086	t	library	2025-11-12 14:38:04.878047+00
f954e1d1-7715-4c04-b162-e52f9fd927f9	9788323133483	t	library	2025-11-12 14:38:04.878047+00
f01b55c0-7103-449e-8a40-2771c94c9284	9788323133483	t	library	2025-11-12 14:38:04.878047+00
20abefd9-b17b-4d5d-8401-d27ba3630b6b	9788323133483	t	library	2025-11-12 14:38:04.878047+00
85b94878-eeca-4000-8f8e-48e756afea0d	9788323133483	t	library	2025-11-12 14:38:04.878047+00
ec59a1d6-0801-4185-b979-d38b230b43a3	9788323133483	t	library	2025-11-12 14:38:04.878047+00
1822f457-05de-4c69-a4ab-f3e8b5ab894d	9788323133483	t	library	2025-11-12 14:38:04.878047+00
c90af170-8433-41b9-8fb5-97335ed0438b	9788323133483	t	library	2025-11-12 14:38:04.878047+00
e3ca4941-2984-4061-88cd-7911b78d217e	9788323133483	t	library	2025-11-12 14:38:04.878047+00
9c0344ef-5f62-47e5-9382-f2a0c0fc5905	9788323133483	t	library	2025-11-12 14:38:04.878047+00
208050ff-4b57-442c-bb84-e3afb3f9d21f	9788323133483	t	library	2025-11-12 14:38:04.878047+00
21aaa60e-517a-4add-a458-cd2d30faf600	9783758437830	t	library	2025-11-12 14:38:04.878047+00
f5a1152e-8bc8-48ba-89db-4192c37b0d06	9783758437830	t	library	2025-11-12 14:38:04.878047+00
c9ddd611-c384-4711-97e1-f078c403cbb4	9783758437830	t	library	2025-11-12 14:38:04.878047+00
080d6386-78ef-4e3e-91f4-d9d435dfa0ba	9783758437830	t	library	2025-11-12 14:38:04.878047+00
49813c29-f5b6-4bc5-a1a1-b7e14b3ecc59	9783758437830	t	library	2025-11-12 14:38:04.878047+00
c2e08e74-3f14-4f30-b001-907777052393	9783758443466	t	library	2025-11-12 14:38:04.878047+00
272427db-f031-41c5-8b44-649e80f3ce6a	9783758443466	t	library	2025-11-12 14:38:04.878047+00
13439432-fbc2-4a95-817d-8be66e153f60	9783758443466	t	library	2025-11-12 14:38:04.878047+00
6e1cc5b2-902e-4b81-a2b6-60d06d7dbfa1	9783758443466	t	library	2025-11-12 14:38:04.878047+00
4af4b23d-8fe6-4af0-ab28-51d8e3ea551c	9783758443466	t	library	2025-11-12 14:38:04.878047+00
9c8bb2f9-46a9-4b67-85c4-27009fb6a675	9783758443466	t	library	2025-11-12 14:38:04.878047+00
dfbd6593-7a95-40ca-bb0c-d4ac837217c7	9783758443466	t	library	2025-11-12 14:38:04.878047+00
a4df852b-3260-4a6b-b157-69fd143993f9	9783758443466	t	library	2025-11-12 14:38:04.878047+00
80da0bee-cec0-4c70-a0dd-ef4388753c4b	9783758443466	t	library	2025-11-12 14:38:04.878047+00
db09f981-926d-4684-bb5a-91b9281406e8	9783758443466	t	library	2025-11-12 14:38:04.878047+00
86482088-fd5a-4ed4-bd68-e7bab97da90a	9783758438240	t	library	2025-11-12 14:38:04.878047+00
877be333-24ff-483c-ab53-33b87caa295c	9783758438240	t	library	2025-11-12 14:38:04.878047+00
24563f30-6b99-45c4-a7aa-b8a443e195be	9783758438240	t	library	2025-11-12 14:38:04.878047+00
c5f20365-2271-4a94-b3ba-566c2e415159	9783758438240	t	library	2025-11-12 14:38:04.878047+00
c15199b4-a5c2-47c3-80f7-de0ee14d9241	9783758438240	t	library	2025-11-12 14:38:04.878047+00
4e55551b-057b-4426-ad50-afd98f01c4a1	9783758438240	t	library	2025-11-12 14:38:04.878047+00
0390c3a6-0940-4671-b333-6054238dc7e1	9783758438240	t	library	2025-11-12 14:38:04.878047+00
ff1497e2-40a7-4099-a1fd-7803790531d4	9783758438240	t	library	2025-11-12 14:38:04.878047+00
fbfd4a17-40d6-4d4c-b284-49211934b6be	9783758438240	t	library	2025-11-12 14:38:04.878047+00
8686c019-a112-417b-b603-d6483610c714	9783758438240	t	library	2025-11-12 14:38:04.878047+00
cd6193f8-667b-4c22-8861-0e3a672da829	9788382309881	t	library	2025-11-12 14:38:04.878047+00
e402a05c-b79c-4bae-93e1-58c1a0a3ee85	9788382309881	t	library	2025-11-12 14:38:04.878047+00
1c774493-6b74-4170-9021-d06ca9b0c078	9788382309881	t	library	2025-11-12 14:38:04.878047+00
b89219ba-2ac3-4e50-acc8-61a48fb7e3ce	9788382309881	t	library	2025-11-12 14:38:04.878047+00
54be30a3-6cd0-4ce9-a923-bbd7994604fd	9788382309881	t	library	2025-11-12 14:38:04.878047+00
c69e4c1f-6f2a-4aef-a3ae-38f0ddb31c1c	9788364208195	t	library	2025-11-12 14:38:04.878047+00
20f6842f-ca6a-4d4a-bc86-d3bbb9b5240d	9788364208195	t	library	2025-11-12 14:38:04.878047+00
e4265bbe-88d7-4d03-b2a1-40beedaef64c	9788364208195	t	library	2025-11-12 14:38:04.878047+00
c1027d9b-ad1f-4364-85a2-679613bd19fa	9788364208195	t	library	2025-11-12 14:38:04.878047+00
4c5f91bc-5627-40e2-b129-871f15cfa351	9788364208195	t	library	2025-11-12 14:38:04.878047+00
69d9a3c2-c3ab-4c12-bba7-b1cd90df68c8	9788364208195	t	library	2025-11-12 14:38:04.878047+00
3fd9fee9-5517-4dbc-a205-62f280f365de	9788375823004	t	library	2025-11-12 14:38:04.878047+00
750d7bf3-ca68-49cd-ac39-1fef91952bb0	9788375823004	t	library	2025-11-12 14:38:04.878047+00
f699984f-6688-407f-8911-b087eb17342c	9788375823004	t	library	2025-11-12 14:38:04.878047+00
626169c5-820d-43b5-b714-74bcbd5e5e85	9788375823004	t	library	2025-11-12 14:38:04.878047+00
804e4e9a-8635-41a7-a177-199a8bfdf7e0	9788375823004	t	library	2025-11-12 14:38:04.878047+00
227ef954-bd51-4393-89c6-fb3051a8be43	9788375823004	t	library	2025-11-12 14:38:04.878047+00
6c7b0d56-b515-4c95-a8aa-7869c70accfe	9788375823004	t	library	2025-11-12 14:38:04.878047+00
b72f2c08-c1ca-4521-acb0-4cf0136821b4	9783758441387	t	library	2025-11-12 14:38:04.878047+00
e1aedf8f-5f86-4b92-b3a7-20daa85b7ab5	9783758441387	t	library	2025-11-12 14:38:04.878047+00
d237735e-9d65-44b6-85ee-e4ef74a53adb	9783758441387	t	library	2025-11-12 14:38:04.878047+00
f70d71ed-4713-4b3e-9c5c-e6ecbc1d09f9	9783758441387	t	library	2025-11-12 14:38:04.878047+00
d496e336-9f39-4cf2-82ea-a3bdcade113b	9783758441387	t	library	2025-11-12 14:38:04.878047+00
457b61d2-d89a-4dac-a97a-bdd5f703434a	9783758441387	t	library	2025-11-12 14:38:04.878047+00
66ef08fc-f5b5-4635-9f6a-282fefb152c2	9783758441387	t	library	2025-11-12 14:38:04.878047+00
67e410fc-b665-4188-8018-e8d31fc12693	9783758441387	t	library	2025-11-12 14:38:04.878047+00
c6998e67-df78-462a-81c7-c4aaa4c13d5a	9788323128830	t	library	2025-11-12 14:38:04.878047+00
e705e5a2-ae86-487a-aea7-9209f6456c48	9788323128830	t	library	2025-11-12 14:38:04.878047+00
3927e818-b344-42a4-bbfe-f5981061bfb8	9788323128830	t	library	2025-11-12 14:38:04.878047+00
a30ddac9-768b-4458-9909-8b2ee592a06a	9788323128830	t	library	2025-11-12 14:38:04.878047+00
23964045-0072-4aef-9127-6015d3defb59	9788323128830	t	library	2025-11-12 14:38:04.878047+00
8b94fa89-b4a3-4695-b579-26eb9f2edcd7	9788323128830	t	library	2025-11-12 14:38:04.878047+00
036c93b6-3ee4-4100-a4e3-1b0e4a79029f	9788323128830	t	library	2025-11-12 14:38:04.878047+00
96ab7968-af8d-4a75-970a-c337f768896c	9788381359764	t	library	2025-11-12 14:38:04.878047+00
cffe8981-6554-4534-880a-4f9ca3fe3a43	9788381359764	t	library	2025-11-12 14:38:04.878047+00
2d10ee25-17f2-4b9e-b76b-a413fc660e6a	9788381359764	t	library	2025-11-12 14:38:04.878047+00
2f7d2308-c996-4bc9-a515-bed23280bd93	9788381359764	t	library	2025-11-12 14:38:04.878047+00
e06edc73-cc4e-4d86-b435-55c1c9a10595	9788381359764	t	library	2025-11-12 14:38:04.878047+00
4199585e-69bb-43bc-91d3-c24e6108640c	9788381359764	t	library	2025-11-12 14:38:04.878047+00
7a9ddbe5-2779-4405-a18c-bd772c9d6bbd	9788381359764	t	library	2025-11-12 14:38:04.878047+00
2f1a9765-34df-400a-ab74-a0c5a3027445	9788381359764	t	library	2025-11-12 14:38:04.878047+00
0a70a67c-c01f-4838-b04c-7326cd7e12f8	9788381359764	t	library	2025-11-12 14:38:04.878047+00
32563b8e-f7ee-4e26-9401-ac1972b3d341	9788381359764	t	library	2025-11-12 14:38:04.878047+00
f94ca789-517e-45e4-b7a6-6fd7a15a0d7f	9788378594086	t	library	2025-11-12 14:38:04.878047+00
94445ad8-6ffb-471f-8a77-c1dfd787d5ca	9788378594086	t	library	2025-11-12 14:38:04.878047+00
1cc0fac8-b0bf-476d-851b-57604596f1d7	9788378594086	t	library	2025-11-12 14:38:04.878047+00
5c10ebcf-d9c2-40db-8772-b27b2830d2ed	9788378594086	t	library	2025-11-12 14:38:04.878047+00
e16120b4-e4f9-4cf1-b5d2-840161ca1bf7	9788378594086	t	library	2025-11-12 14:38:04.878047+00
375f6f50-8d24-4d1b-b7bf-61db6bfddc1e	9788378594086	t	library	2025-11-12 14:38:04.878047+00
edb455a2-8d02-49ef-a8b9-c199e6fcd23c	9788378594086	t	library	2025-11-12 14:38:04.878047+00
af65cb99-db51-40ab-96d6-600ab49193bd	9788378594086	t	library	2025-11-12 14:38:04.878047+00
1e1ad039-e9de-45a0-a2b8-5617a02d2503	9788378594086	t	library	2025-11-12 14:38:04.878047+00
7bc73332-9bba-4f16-b81f-9166bf7504a7	9788376706405	t	library	2025-11-12 14:38:04.878047+00
b13ff13c-09cf-448a-864a-0fd43c70a6e9	9788376706405	t	library	2025-11-12 14:38:04.878047+00
5834a67e-beb5-4b85-b902-4663dd79579f	9788376706405	t	library	2025-11-12 14:38:04.878047+00
4af652a4-a302-4c9a-a510-036d1c916f67	9788376706405	t	library	2025-11-12 14:38:04.878047+00
6fdf8388-39aa-4976-92f5-588d123d08d7	9788376706405	t	library	2025-11-12 14:38:04.878047+00
843477d8-1bc5-4ac5-b0e8-a7feff22774b	9788376706405	t	library	2025-11-12 14:38:04.878047+00
7f0ca1f2-af46-4c0f-bb88-404a74c50165	9788376706405	t	library	2025-11-12 14:38:04.878047+00
cebbc6cd-c1ff-425c-8222-d9beba1bb734	9788376706405	t	library	2025-11-12 14:38:04.878047+00
dd4fac0c-805b-447f-aba5-b3d87315d978	9788376706405	t	library	2025-11-12 14:38:04.878047+00
f8036a3b-967c-4a93-b13a-f2a8abe71a2e	9788376706405	t	library	2025-11-12 14:38:04.878047+00
4617bc00-e73b-412d-81ac-39082537d667	9788381105316	t	library	2025-11-12 14:38:04.878047+00
2b8b54d5-db19-4fd6-aff2-ca7678fff822	9788381105316	t	library	2025-11-12 14:38:04.878047+00
d6614627-4d92-421f-96a7-de1633b9b66a	9788381105316	t	library	2025-11-12 14:38:04.878047+00
4166eea9-577f-4b52-9fb7-6928474b134d	9788381105316	t	library	2025-11-12 14:38:04.878047+00
ddfe9eff-3d32-4653-9fb8-05cdcfbe79fa	9788381105316	t	library	2025-11-12 14:38:04.878047+00
fc760af4-3a10-419f-a84b-092cb599fe40	9788324036011	t	library	2025-11-12 14:38:04.878047+00
e59b1d73-3143-42f6-9be9-514608e51051	9788324036011	t	library	2025-11-12 14:38:04.878047+00
2213acda-1c09-4275-a689-aa8f848da74d	9788324036011	t	library	2025-11-12 14:38:04.878047+00
e1203b9a-f783-4290-a4fc-8eac4048705d	9788324036011	t	library	2025-11-12 14:38:04.878047+00
a05ad894-ee98-4875-b80b-86bbc2729566	9788324036011	t	library	2025-11-12 14:38:04.878047+00
a6238847-f846-4cb0-9dce-ba6bbdef1531	9788324036011	t	library	2025-11-12 14:38:04.878047+00
2cdbfc42-c379-40eb-9612-cafc1b135119	9788324036011	t	library	2025-11-12 14:38:04.878047+00
e02c8bb0-788f-497e-ab05-e76d526d4e0d	9788324036011	t	library	2025-11-12 14:38:04.878047+00
dee87927-e800-4649-9db6-b221406c419b	9788324036011	t	library	2025-11-12 14:38:04.878047+00
ab8df273-68e8-497a-a16a-91613b82296b	9788324036011	t	library	2025-11-12 14:38:04.878047+00
4e5da0e7-73a9-44ed-8497-0736204effe8	9782808694544	t	library	2025-11-12 14:38:04.878047+00
e741692a-cd1c-4322-bc44-3caadfaf2ca7	9782808694544	t	library	2025-11-12 14:38:04.878047+00
9a90a199-67d7-4042-b552-8b3816f2fc96	9782808694544	t	library	2025-11-12 14:38:04.878047+00
15f35591-d526-4e81-be28-1facad747e27	9782808694544	t	library	2025-11-12 14:38:04.878047+00
a23f8720-c760-4862-b756-2b5c17f241b7	9782808694544	t	library	2025-11-12 14:38:04.878047+00
fd45a848-3844-4e0e-8485-8890681af87e	9782808694544	t	library	2025-11-12 14:38:04.878047+00
f17592a1-45d2-40c3-a30f-e9289d32f1cf	9782808694544	t	library	2025-11-12 14:38:04.878047+00
e3a11942-7214-493d-9b4b-3d8d4473cfb6	9782808694544	t	library	2025-11-12 14:38:04.878047+00
a696e9ac-f9e2-4107-8911-7b4c1a2cbaf0	9782808694544	t	library	2025-11-12 14:38:04.878047+00
23d80817-dd43-44e8-aff6-3c447192207f	9788727084572	t	library	2025-11-12 14:38:04.878047+00
885547ca-28a1-41d3-9d4f-421d602a6b7b	9788727084572	t	library	2025-11-12 14:38:04.878047+00
be30b526-8881-4d9d-a586-7bf81902d620	9788727084572	t	library	2025-11-12 14:38:04.878047+00
cf03bff8-1617-4193-bdf9-635f71faa3c3	9788727084572	t	library	2025-11-12 14:38:04.878047+00
105f83ff-d3b7-4ada-95fe-4f8090c4c5d7	9788727084572	t	library	2025-11-12 14:38:04.878047+00
f0bddae9-0ac9-4b82-9a18-24d0ea34c0dc	9788727084572	t	library	2025-11-12 14:38:04.878047+00
08f735cc-b081-47aa-b6ac-9fae11f18586	9788727084572	t	library	2025-11-12 14:38:04.878047+00
6a48c1a9-8202-46fb-b714-114e07f6c1a4	9788727084572	t	library	2025-11-12 14:38:04.878047+00
470a382f-fc97-4448-920a-523a4d30bc99	9788328097124	t	library	2025-11-12 14:38:04.878047+00
dbb7123f-4905-4057-9646-5e7118024d71	9788328097124	t	library	2025-11-12 14:38:04.878047+00
e4b847b5-06c6-4b21-8eba-3215a6c7eb3d	9788328097124	t	library	2025-11-12 14:38:04.878047+00
0f13895b-88a0-4f08-83eb-765110cb1e75	9788328097124	t	library	2025-11-12 14:38:04.878047+00
28ad9eed-d42e-4b0c-8a65-38f07e38d1e2	9788328097124	t	library	2025-11-12 14:38:04.878047+00
31365c97-44e0-440b-b020-95dedb742867	9788324079513	t	library	2025-11-12 14:38:04.878047+00
59794419-1244-4757-b187-46bf901733a3	9788324079513	t	library	2025-11-12 14:38:04.878047+00
9aeea6d5-81b9-4c75-a93f-70991e73d8f5	9788324079513	t	library	2025-11-12 14:38:04.878047+00
5788bc30-5fc2-406e-9f93-e5218a794ac0	9788324079513	t	library	2025-11-12 14:38:04.878047+00
014b2198-23b5-4425-aa01-37cce548431c	9788324079513	t	library	2025-11-12 14:38:04.878047+00
9b2818bf-04e8-4352-a52d-8328886c8cc0	9788324079513	t	library	2025-11-12 14:38:04.878047+00
69279d19-7aa0-4a6a-aeba-04e14230e1e5	9788324079513	t	library	2025-11-12 14:38:04.878047+00
1ba962bd-bf27-4e5e-acf9-c0a8452da1bd	9788324079513	t	library	2025-11-12 14:38:04.878047+00
357cdef3-5fd1-4fc3-ac7e-592c31bebede	9788324044238	t	library	2025-11-12 14:38:04.878047+00
9041f583-8a86-440f-9a73-8b26e764b043	9788324044238	t	library	2025-11-12 14:38:04.878047+00
cd08c3f9-e5bc-47d2-aed0-d4e4c70d789a	9788324044238	t	library	2025-11-12 14:38:04.878047+00
238d122e-2eb4-4c8b-8332-d03d605e3480	9788324044238	t	library	2025-11-12 14:38:04.878047+00
49354bc9-7065-4653-84c7-88e30aceb8d8	9788324044238	t	library	2025-11-12 14:38:04.878047+00
bd6f4af0-fcb6-4a84-8f7f-73d55515e327	9788324044238	t	library	2025-11-12 14:38:04.878047+00
9baaf160-1ce3-4980-ae22-8d079280bf4e	9782322469536	t	library	2025-11-12 14:38:04.878047+00
e88cfb69-f8f9-448b-bdd8-2bc0ccf0bc4c	9782322469536	t	library	2025-11-12 14:38:04.878047+00
422321fc-9261-4fe1-a4d5-9367db1762f4	9782322469536	t	library	2025-11-12 14:38:04.878047+00
28155808-21d8-4a60-88c2-5378a6b8de93	9782322469536	t	library	2025-11-12 14:38:04.878047+00
de653a8a-8e8c-46c0-a456-b4022041b52f	9782322469536	t	library	2025-11-12 14:38:04.878047+00
7bc29414-86f3-4827-82d1-3cff93535d37	9782322469536	t	library	2025-11-12 14:38:04.878047+00
40dce012-4c55-49a6-9076-5d9c001b6058	9782322469536	t	library	2025-11-12 14:38:04.878047+00
31281218-bd3b-45e6-b2e6-6ffb22f05987	9788727088563	t	library	2025-11-12 14:38:04.878047+00
543ac6c0-b657-4171-b35c-21d30227ee4b	9788727088563	t	library	2025-11-12 14:38:04.878047+00
1828077f-783b-40b9-8762-c480112a4c17	9788727088563	t	library	2025-11-12 14:38:04.878047+00
edd9bca0-b587-42f2-8675-334cbd05936e	9788727088563	t	library	2025-11-12 14:38:04.878047+00
51691043-3a54-49b4-a607-7018148c4bf7	9788727088563	t	library	2025-11-12 14:38:04.878047+00
524960bf-1a1e-4d77-b8da-b03a19acc207	9788727088563	t	library	2025-11-12 14:38:04.878047+00
493de335-65ef-4ede-ac59-9ddf19983cd7	9788727088563	t	library	2025-11-12 14:38:04.878047+00
9b7e0411-abd3-402c-8cc0-cfb528f73568	9788727088563	t	library	2025-11-12 14:38:04.878047+00
bdd4865e-7a04-4119-9df4-280be3998a29	9788727088563	t	library	2025-11-12 14:38:04.878047+00
8c67aa32-5c5c-4a73-b60f-9862c6a7cff7	9788090947603	t	library	2025-11-12 14:38:04.878047+00
7e9b1066-e561-4204-8005-3ff581ab851b	9788090947603	t	library	2025-11-12 14:38:04.878047+00
771a9178-a00b-4053-bfb4-9755d20c2cd0	9788090947603	t	library	2025-11-12 14:38:04.878047+00
f0483e5b-e75c-4f5b-8d6e-9ae018980ed9	9788090947603	t	library	2025-11-12 14:38:04.878047+00
97dd10ba-5f29-421b-9511-eb9ecb87c63c	9788090947603	t	library	2025-11-12 14:38:04.878047+00
f7ddd4ba-8b2a-497a-be3b-14a4a3d8f05e	9788090947603	t	library	2025-11-12 14:38:04.878047+00
74f5753c-746e-4985-9081-46d67dda1dfe	9788323135999	t	library	2025-11-12 14:38:04.878047+00
c3dccd52-5a4a-4e75-a5c5-5c96cd8079cd	9788323135999	t	library	2025-11-12 14:38:04.878047+00
2c5adba6-b1d4-4c69-8ae2-f42b73f470c8	9788323135999	t	library	2025-11-12 14:38:04.878047+00
65b4978b-dd2c-4109-b56e-79ce5602dd4e	9788323135999	t	library	2025-11-12 14:38:04.878047+00
8e302d0a-010c-49d4-82cb-dce7c3795674	9788323135999	t	library	2025-11-12 14:38:04.878047+00
2dbcc727-d951-427d-b72f-dc4abd8707f1	9788323135999	t	library	2025-11-12 14:38:04.878047+00
a1641507-b926-402b-9ac0-56b2fcb82004	9788324066292	t	library	2025-11-12 14:38:04.878047+00
835a7626-dda3-427c-9944-e0977c8d25cd	9788324066292	t	library	2025-11-12 14:38:04.878047+00
cc8e1229-141d-44b5-ab27-dcd78ab0b5f9	9788324066292	t	library	2025-11-12 14:38:04.878047+00
03e490a1-e74b-409e-b826-ca6e3bba0eb2	9788324066292	t	library	2025-11-12 14:38:04.878047+00
950acd18-1cc7-4344-9cdb-a98051ccdadc	9788324066292	t	library	2025-11-12 14:38:04.878047+00
d42c3fac-0f2f-4a9d-8191-430fd63cb13b	9788324066292	t	library	2025-11-12 14:38:04.878047+00
ac523d2a-ec5b-42a1-a7c3-3ae72cf37dfb	9788324066292	t	library	2025-11-12 14:38:04.878047+00
a5c936a8-7ee7-429f-a1ab-90ddcac3e411	9788324066292	t	library	2025-11-12 14:38:04.878047+00
17a9cf75-e93f-4bc9-806c-3c17f2264e47	9788324066292	t	library	2025-11-12 14:38:04.878047+00
af91e91a-81f8-47fb-a9e2-5c7baa69bd2b	9788395522772	t	library	2025-11-12 14:38:04.878047+00
19fd67a7-29cc-454e-adb6-1fc13fc5c697	9788395522772	t	library	2025-11-12 14:38:04.878047+00
fafb37cc-face-4aa0-b880-c1679eb0790b	9788395522772	t	library	2025-11-12 14:38:04.878047+00
49831496-acb4-4d11-9a61-30c3767af743	9788395522772	t	library	2025-11-12 14:38:04.878047+00
39d0d1b6-4754-439a-9c22-4b83535abc20	9788395522772	t	library	2025-11-12 14:38:04.878047+00
c58c0e18-d97d-445b-aa99-ae63586cd3e2	9788395522772	t	library	2025-11-12 14:38:04.878047+00
c3447596-3144-4e45-9f13-346b3e537e07	9788395522772	t	library	2025-11-12 14:38:04.878047+00
566586d1-be73-4598-abbe-eb52982f1795	9788395522772	t	library	2025-11-12 14:38:04.878047+00
b9ddb8d4-81fc-4af9-afcf-dc2e99ba0c20	9788396262554	t	library	2025-11-12 14:38:04.878047+00
7d754733-d619-4a1e-be19-b1cd1bb85db1	9788396262554	t	library	2025-11-12 14:38:04.878047+00
48169b0b-f2ad-470e-9595-ee636809e2f0	9788396262554	t	library	2025-11-12 14:38:04.878047+00
c8489a7d-c62c-47c1-ad2e-92875b8dc25e	9788396262554	t	library	2025-11-12 14:38:04.878047+00
7b9ec7a2-da2d-40d7-a49a-ec5bb68b79bc	9788396262554	t	library	2025-11-12 14:38:04.878047+00
ec8f0788-99c4-4bf5-83b4-60aa456254ba	9788396262554	t	library	2025-11-12 14:38:04.878047+00
0c715cf4-bb49-4434-92ed-ff77b75b22c7	9788396262554	t	library	2025-11-12 14:38:04.878047+00
666e2661-c12c-45b9-bf34-5196cf70cf9c	9788396262554	t	library	2025-11-12 14:38:04.878047+00
cd645bf7-a175-453e-8744-8c5f3191873e	9788396262554	t	library	2025-11-12 14:38:04.878047+00
2bbead1d-f46e-43ba-88d2-841aa6ad55ba	9788323138303	t	library	2025-11-12 14:38:04.878047+00
a1aa1fba-b324-4a68-91f8-2a6792ff8f52	9788323138303	t	library	2025-11-12 14:38:04.878047+00
64f61045-4181-4852-9025-aa0bc1ff2e5a	9788323138303	t	library	2025-11-12 14:38:04.878047+00
bbf79f5c-6622-4812-abf8-3c42e6397c17	9788323138303	t	library	2025-11-12 14:38:04.878047+00
10c7e798-a841-477a-beea-5da189806545	9788323138303	t	library	2025-11-12 14:38:04.878047+00
bd0f1973-624c-49d4-bb46-a3ea5cf4b58e	9788323138303	t	library	2025-11-12 14:38:04.878047+00
0266ed22-2e19-4582-a9d3-3e39683d1a96	9788323138303	t	library	2025-11-12 14:38:04.878047+00
93b66e1d-90ab-467e-857d-9759efce428e	9788323138303	t	library	2025-11-12 14:38:04.878047+00
dacb7888-cdcb-429a-a46a-91f0a78248b3	9788382101928	t	library	2025-11-12 14:38:04.878047+00
13babec4-10e2-4e49-a30f-547c0e3a1d88	9788382101928	t	library	2025-11-12 14:38:04.878047+00
1300e6fb-aac6-4313-8512-f16f0b8b664d	9788382101928	t	library	2025-11-12 14:38:04.878047+00
7bfc2546-9e4f-4665-9a3b-1c4a4e9292b5	9788382101928	t	library	2025-11-12 14:38:04.878047+00
cf7e2f2b-8fe4-450e-bdb9-e6279ff83a50	9788382101928	t	library	2025-11-12 14:38:04.878047+00
3936a895-586a-425e-85ea-3bc303ffca01	9788382101928	t	library	2025-11-12 14:38:04.878047+00
5588c091-ce3f-4888-96ca-09f6a9c384d6	9788382101928	t	library	2025-11-12 14:38:04.878047+00
efc48159-d3ee-4f4c-8f6c-6f9cf465c657	9788382300987	t	library	2025-11-12 14:38:04.878047+00
b644ecdb-192e-4424-aafb-e551f5a2e81b	9788382300987	t	library	2025-11-12 14:38:04.878047+00
e2fc5ab8-c9bf-4aa0-b898-384555f03324	9788382300987	t	library	2025-11-12 14:38:04.878047+00
2187ec04-a184-478f-85c4-b5b2adabd3c8	9788382300987	t	library	2025-11-12 14:38:04.878047+00
a13edf68-f7b1-4a2d-ad79-971baeb1b02a	9788382300987	t	library	2025-11-12 14:38:04.878047+00
6be1bcea-f1f2-4ab2-a586-76e7b0d1b8e0	9788382300987	t	library	2025-11-12 14:38:04.878047+00
5e09b7f8-7d68-414e-8d5e-b9d54db8fb2e	9788324040421	t	library	2025-11-12 14:38:04.878047+00
d185b6b5-3ed9-4094-abbf-391d8706de3b	9788324040421	t	library	2025-11-12 14:38:04.878047+00
1746490a-7492-4805-967c-f09be426a1d2	9788324040421	t	library	2025-11-12 14:38:04.878047+00
0e556d36-5040-4e3d-830f-08e9c0bedec3	9788324040421	t	library	2025-11-12 14:38:04.878047+00
c30fbfee-442a-4dec-a5b6-4fe8c0a5d83f	9788324040421	t	library	2025-11-12 14:38:04.878047+00
6db9ae37-e4ca-4fdb-917b-03c1e7fb70ea	9788324040421	t	library	2025-11-12 14:38:04.878047+00
274aa8ce-1205-4134-bfff-8482fef123a6	9788324040421	t	library	2025-11-12 14:38:04.878047+00
9bd0d34c-13a5-4946-a41b-a122144fca73	9788324040421	t	library	2025-11-12 14:38:04.878047+00
051c2885-d4a5-46ae-b698-9487bf5e5628	9788324062058	t	library	2025-11-12 14:38:04.878047+00
7e33e90c-cf65-4899-8261-d728cb651e23	9788324062058	t	library	2025-11-12 14:38:04.878047+00
209eadeb-82b4-4f83-889f-85e860d6fa24	9788324062058	t	library	2025-11-12 14:38:04.878047+00
92b0306a-73df-4465-9b78-2724ff6b1088	9788324062058	t	library	2025-11-12 14:38:04.878047+00
d3a741fc-6f0d-40b1-9104-c94e71d99342	9788324062058	t	library	2025-11-12 14:38:04.878047+00
8b92bcdc-ccd7-49ee-a5d2-a0399d0cd53c	9788324062058	t	library	2025-11-12 14:38:04.878047+00
87fe4d8d-5bad-45dd-bce1-7099ec06186c	9788324062058	t	library	2025-11-12 14:38:04.878047+00
b7477517-b809-4a49-8d13-49dd675799f6	9788324062058	t	library	2025-11-12 14:38:04.878047+00
12fa5ee1-69d0-4b00-872f-756430c592fd	9788324061518	t	library	2025-11-12 14:38:04.878047+00
c592efac-acd2-400a-8dca-11ee8d1a0843	9788324061518	t	library	2025-11-12 14:38:04.878047+00
49ff5e68-7736-42cb-ae1e-a359b33243c3	9788324061518	t	library	2025-11-12 14:38:04.878047+00
af66bc9a-00d9-4778-9322-9aa17c9a3283	9788324061518	t	library	2025-11-12 14:38:04.878047+00
062cb186-5583-4a68-bf94-8d24b726ea53	9788324061518	t	library	2025-11-12 14:38:04.878047+00
e7dac917-23b6-4715-aae6-e30b5d206fb5	9788324061518	t	library	2025-11-12 14:38:04.878047+00
a0812f0a-3700-448e-9c58-42efff5a53c0	9788324061518	t	library	2025-11-12 14:38:04.878047+00
9ba71904-54da-4305-b796-922b480c84f4	9788324061518	t	library	2025-11-12 14:38:04.878047+00
58defc1e-85e0-4d3f-a4a6-3d23aa7f4bd2	9788324062713	t	library	2025-11-12 14:38:04.878047+00
0673757f-009f-4aa1-87a4-e8e11e87dd87	9788324062713	t	library	2025-11-12 14:38:04.878047+00
72913ffd-8eca-45c3-969e-6191aa7cea1d	9788324062713	t	library	2025-11-12 14:38:04.878047+00
39fc95a1-6ef5-40a9-a5c4-373118ecdb55	9788324062713	t	library	2025-11-12 14:38:04.878047+00
fdcf4493-841b-497b-b9b6-737b4ddbc4dc	9788324062713	t	library	2025-11-12 14:38:04.878047+00
7f7e87a3-e843-4f27-83da-73decd0d4373	9788324062713	t	library	2025-11-12 14:38:04.878047+00
0e3b817b-15e9-4d56-8c18-514fc80475c9	9788324062713	t	library	2025-11-12 14:38:04.878047+00
ac5ef001-9c77-44b3-ad71-03870f143df0	9788380539693	t	library	2025-11-12 14:38:04.878047+00
0c7806c7-0ca7-41ff-a808-3637f3512673	9788380539693	t	library	2025-11-12 14:38:04.878047+00
4d2cd315-ab6d-47e6-bb75-9e7eae41bfd5	9788380539693	t	library	2025-11-12 14:38:04.878047+00
71e13851-0a4a-455b-80a4-6e5be5363346	9788380539693	t	library	2025-11-12 14:38:04.878047+00
45518952-f6d8-4fae-bdeb-b02a6b9aa9e9	9788380539693	t	library	2025-11-12 14:38:04.878047+00
d9a26ec4-1257-4b93-b1be-790b7cd99317	9788380539693	t	library	2025-11-12 14:38:04.878047+00
5666472d-d64e-4bca-bd60-f0e0c4baa4b6	9788380539693	t	library	2025-11-12 14:38:04.878047+00
dd9d6908-06ff-48ac-a9ed-f418a1908789	9788379241132	t	library	2025-11-12 14:38:04.878047+00
4423d593-bb12-4aff-9588-f26628a71035	9788379241132	t	library	2025-11-12 14:38:04.878047+00
5214c27b-5cc4-45a1-9ac4-24dbee4fc187	9788379241132	t	library	2025-11-12 14:38:04.878047+00
55eed3fa-6692-4726-a118-7f7169ad7290	9788379241132	t	library	2025-11-12 14:38:04.878047+00
2ac5a65b-324b-4f71-a3ab-64f5acb41af2	9788379241132	t	library	2025-11-12 14:38:04.878047+00
496f7e65-cb75-46d9-a72e-f8bb0e301f7b	9788379241132	t	library	2025-11-12 14:38:04.878047+00
7bfcc2f2-b1d7-4068-9934-f47c5016bc92	9788394479534	t	library	2025-11-12 14:38:04.878047+00
c0d887b4-05d3-4d36-8c5c-94f494feb368	9788394479534	t	library	2025-11-12 14:38:04.878047+00
984a9049-980c-47c0-b552-7c3458590f50	9788394479534	t	library	2025-11-12 14:38:04.878047+00
eb520f48-421c-41ea-90d5-3a0715ad5186	9788394479534	t	library	2025-11-12 14:38:04.878047+00
aa1e666b-8a81-49a2-b173-1a606d2fd09f	9788394479534	t	library	2025-11-12 14:38:04.878047+00
896c66af-0213-4e5d-ae6e-05d301227f32	9788394479534	t	library	2025-11-12 14:38:04.878047+00
6ba8566f-1809-48e5-a789-ff07aa943643	9788394479534	t	library	2025-11-12 14:38:04.878047+00
f0b5c83a-9a4c-4ac2-bce8-325641c993a2	9788382109795	t	library	2025-11-12 14:38:04.878047+00
688e6117-b86f-4be4-8ac0-b76478a7319d	9788382109795	t	library	2025-11-12 14:38:04.878047+00
b29d984b-d97a-44ac-9f48-91b3be3cb165	9788382109795	t	library	2025-11-12 14:38:04.878047+00
5ae2f3d8-1181-4f23-a22b-d70760d944d1	9788382109795	t	library	2025-11-12 14:38:04.878047+00
d1c12fef-f9df-4428-a0db-f05d65f602a0	9788382109795	t	library	2025-11-12 14:38:04.878047+00
0bbcd209-1e30-4b95-94b1-7ad4e004ee7b	9788381296786	t	library	2025-11-12 14:38:04.878047+00
62fbca09-776e-4fb1-b629-ca1a6c63a0d9	9788381296786	t	library	2025-11-12 14:38:04.878047+00
dc910316-e4da-4828-8650-64409ca2444f	9788381296786	t	library	2025-11-12 14:38:04.878047+00
5218eacf-0a16-4e60-ba54-4feaa46a3cc7	9788381296786	t	library	2025-11-12 14:38:04.878047+00
6490ed73-ce6f-4d0f-8386-875980844656	9788381296786	t	library	2025-11-12 14:38:04.878047+00
9c9fcfd7-76d2-4e7c-bf50-fb74fc89b025	9788381296786	t	library	2025-11-12 14:38:04.878047+00
7ef9f46a-35e6-4670-8ad4-06a8777932f2	9788381296786	t	library	2025-11-12 14:38:04.878047+00
db994379-c446-4926-969e-1a86fb4292da	9788381296786	t	library	2025-11-12 14:38:04.878047+00
8ec1ccee-a48c-4842-835c-b689ef6048f5	9788381296786	t	library	2025-11-12 14:38:04.878047+00
723fc7b9-7092-4b70-8243-882a875c4409	9788381296786	t	library	2025-11-12 14:38:04.878047+00
bd2be155-fcb9-45bc-b60e-e0fdef123e07	9788379246199	t	library	2025-11-12 14:38:04.878047+00
dc679cca-6b74-44cc-a9dc-c888b22029c4	9788379246199	t	library	2025-11-12 14:38:04.878047+00
df7783f6-1c82-4ed1-890b-ce142c957976	9788379246199	t	library	2025-11-12 14:38:04.878047+00
17034d31-8b3b-4633-bfce-9a3d766e537c	9788379246199	t	library	2025-11-12 14:38:04.878047+00
46894436-83cc-4d90-81f2-54a37b66f4b5	9788379246199	t	library	2025-11-12 14:38:04.878047+00
197a8c33-6c0f-4308-91d5-0a0beb9c12b0	9788379246199	t	library	2025-11-12 14:38:04.878047+00
87ceb2d9-68a1-43e4-baa6-0c3a9c90f4d8	9788379246199	t	library	2025-11-12 14:38:04.878047+00
2134f1b0-c190-43b0-9705-9320134ab4f9	9788379246199	t	library	2025-11-12 14:38:04.878047+00
848069a5-f237-4b16-8d5f-56fe049f73ab	9788379246199	t	library	2025-11-12 14:38:04.878047+00
641edb70-2647-4b7a-ac31-6611bf36fbd8	9788383307275	t	library	2025-11-12 14:38:04.878047+00
8922b301-d5f1-4325-b00a-496ac812afe9	9788383307275	t	library	2025-11-12 14:38:04.878047+00
483c8c88-ee41-4e2d-9ae9-71907ee2b89d	9788383307275	t	library	2025-11-12 14:38:04.878047+00
495d07ed-a895-4362-8b41-3f87c33846dc	9788383307275	t	library	2025-11-12 14:38:04.878047+00
b04b5764-1a7c-4c73-801e-96c8cc109a28	9788383307275	t	library	2025-11-12 14:38:04.878047+00
23950bae-1423-4514-b01c-94d7f5bd2310	9788383307275	t	library	2025-11-12 14:38:04.878047+00
64049401-5532-45aa-9d2b-503f6fd80fba	9788383307275	t	library	2025-11-12 14:38:04.878047+00
e22a59cf-f044-4475-ad85-c86e2dcd32c6	9788324034413	t	library	2025-11-12 14:38:04.878047+00
f444368f-fb86-45b1-ad43-a46ad90e4f91	9788324034413	t	library	2025-11-12 14:38:04.878047+00
78f70083-bfbe-40f9-9cc3-3aa958d7a235	9788324034413	t	library	2025-11-12 14:38:04.878047+00
095dc6ee-9288-4781-9e95-269bc84a36d9	9788324034413	t	library	2025-11-12 14:38:04.878047+00
e3d9580c-6148-4a27-81ef-cb043ec7ae31	9788324034413	t	library	2025-11-12 14:38:04.878047+00
a37bd5cb-2b2b-4696-bf6d-c16ad51a0802	9788324034413	t	library	2025-11-12 14:38:04.878047+00
9c680c0f-ee2b-4bbc-98d3-28b4fda21150	9788324034413	t	library	2025-11-12 14:38:04.878047+00
1276ea8f-c7e5-4fb1-89b5-65d112ce66f8	9788324034413	t	library	2025-11-12 14:38:04.878047+00
09cf89d3-4fee-4f2a-9e81-ae40c6004e74	9788324034413	t	library	2025-11-12 14:38:04.878047+00
5967c3fd-9570-4c54-addc-c818d3c8cf60	9788324034413	t	library	2025-11-12 14:38:04.878047+00
42fad007-9589-4c27-8604-765944a17219	9788328098305	t	library	2025-11-12 14:38:04.878047+00
de207faf-6dfc-4cc0-9871-966ee31bb24c	9788328098305	t	library	2025-11-12 14:38:04.878047+00
47144b4d-9c45-439d-8e8e-ef51b9eb1322	9788328098305	t	library	2025-11-12 14:38:04.878047+00
ed091f4a-9f37-4bf5-86e5-957f1bb0c6a3	9788328098305	t	library	2025-11-12 14:38:04.878047+00
36fcc77e-61b4-4598-a3ee-5c9444426f59	9788328098305	t	library	2025-11-12 14:38:04.878047+00
9f2a84b6-ef55-4d2e-a69a-43caf0df69a9	9788328098305	t	library	2025-11-12 14:38:04.878047+00
246f9fbf-5890-48cb-8b29-fd3c96e7969e	9788324086689	t	library	2025-11-12 14:38:04.878047+00
54d9a443-568d-4e0a-bcea-3b6c8b1d381f	9788324086689	t	library	2025-11-12 14:38:04.878047+00
d2b16ad6-c0b1-4e20-b6e1-3d606807fb1f	9788324086689	t	library	2025-11-12 14:38:04.878047+00
261743b3-ab8e-4269-893e-5a478af1eea2	9788324086689	t	library	2025-11-12 14:38:04.878047+00
8626c8cd-c351-464f-a2f8-09297b281b7a	9788324086689	t	library	2025-11-12 14:38:04.878047+00
0f966829-d881-46fa-a79c-671277651d01	9788324063529	t	library	2025-11-12 14:38:04.878047+00
e41e72dc-386a-4228-88f8-7f6b8403dbcf	9788324063529	t	library	2025-11-12 14:38:04.878047+00
2d16ac22-66e6-4a9f-b86a-c8608f014f10	9788324063529	t	library	2025-11-12 14:38:04.878047+00
2cfaa694-2185-47e6-b55f-aff28d9d5aba	9788324063529	t	library	2025-11-12 14:38:04.878047+00
b6e73a2e-2b5c-49ea-8c9f-4c8ddf1e7faf	9788324063529	t	library	2025-11-12 14:38:04.878047+00
a6e65fec-2603-4a37-bff3-bb5d988f6d6e	9788324063529	t	library	2025-11-12 14:38:04.878047+00
1cac7555-b9b4-41fc-a66d-224863cec834	9788324063529	t	library	2025-11-12 14:38:04.878047+00
af658893-18ca-402f-9778-9cd964b75c41	9788324063529	t	library	2025-11-12 14:38:04.878047+00
18f79544-435b-4b85-b989-9a1daddc486a	9788324063529	t	library	2025-11-12 14:38:04.878047+00
\.


--
-- Data for Name: cart; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.cart (id, user_id, status, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: cart_item; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.cart_item (id, cart_id, isbn, quantity, added_at) FROM stdin;
\.


--
-- Data for Name: locker; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.locker (id, locker_code, street, city, postal_code, location) FROM stdin;
dbf6eca1-4adb-4a8d-be05-a638e0db10fb	WRO-PWR	Wybrzeże Stanisława Wyspiańskiego 27	Wrocław	50-370	0101000020E610000039B4C876BE0F3140849ECDAACF8D4940
03d09d1b-c39b-4ab1-8a9b-4d7a50448681	WRO-RYN	Rynek 1	Wrocław	50-438	0101000020E61000007FD93D795808314012A5BDC1178E4940
db1e2f75-d2d4-4a3c-b6de-90f28613a1e1	WRO-DWR	Józefa Piłsudskiego 105	Wrocław	50-046	0101000020E610000027A089B0E1093140068195438B8C4940
\.


--
-- Data for Name: locker_box; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.locker_box (id, locker_id, number, is_available) FROM stdin;
4f861687-146f-4ca6-9cec-0612964fb9ec	dbf6eca1-4adb-4a8d-be05-a638e0db10fb	1	t
faaff8d3-1bc5-4234-bf2b-6eee7fe28a2e	dbf6eca1-4adb-4a8d-be05-a638e0db10fb	2	t
25386550-6273-46df-836b-dbc9c36e7dcd	dbf6eca1-4adb-4a8d-be05-a638e0db10fb	3	t
bc45eba2-0812-4761-afca-493ccedb8b62	dbf6eca1-4adb-4a8d-be05-a638e0db10fb	4	t
bef6b0a2-4963-4bde-a72a-b8189d522cbd	dbf6eca1-4adb-4a8d-be05-a638e0db10fb	5	t
7a7b9b8b-d32e-4b54-8e02-89113060f592	dbf6eca1-4adb-4a8d-be05-a638e0db10fb	6	t
ef408bbc-1cc5-4798-9812-aae3056a0895	dbf6eca1-4adb-4a8d-be05-a638e0db10fb	7	t
126d23dc-0ec9-47a0-9cb5-00fb62d0ddce	dbf6eca1-4adb-4a8d-be05-a638e0db10fb	8	t
be9627f9-56de-4a88-a0c7-844b01f2957e	dbf6eca1-4adb-4a8d-be05-a638e0db10fb	9	t
760fb5d7-bd0b-4760-b0b0-2893dd1d7f82	dbf6eca1-4adb-4a8d-be05-a638e0db10fb	10	t
6d1ca453-6135-4705-a85b-9a3b5276da1a	03d09d1b-c39b-4ab1-8a9b-4d7a50448681	1	t
864fc509-7633-4356-9adb-9be215389189	03d09d1b-c39b-4ab1-8a9b-4d7a50448681	2	t
1014e446-29f2-4f82-9a48-7bfccbf604c6	03d09d1b-c39b-4ab1-8a9b-4d7a50448681	3	t
0f53c908-a289-43ca-b182-52fb5352e4b1	03d09d1b-c39b-4ab1-8a9b-4d7a50448681	4	t
4f978c00-ddda-4d69-9ad4-c6cc028b3635	03d09d1b-c39b-4ab1-8a9b-4d7a50448681	5	t
9ed9eb9c-5d1f-4a27-b40a-d7de0525658a	03d09d1b-c39b-4ab1-8a9b-4d7a50448681	6	t
9331dd05-784b-4939-9afe-f1c81cb91169	03d09d1b-c39b-4ab1-8a9b-4d7a50448681	7	t
7b367ac9-57f3-4fed-8762-afba090e6424	03d09d1b-c39b-4ab1-8a9b-4d7a50448681	8	t
e5cad7d4-26cc-47c4-a23c-c3c5b5f2abb2	03d09d1b-c39b-4ab1-8a9b-4d7a50448681	9	t
68081cd6-8ff3-4139-ad11-980938836e0b	03d09d1b-c39b-4ab1-8a9b-4d7a50448681	10	t
47a11b3d-9cbb-4690-a82e-9cae8913785c	db1e2f75-d2d4-4a3c-b6de-90f28613a1e1	1	t
f40e7352-4c95-41f9-9377-ce061fd5f523	db1e2f75-d2d4-4a3c-b6de-90f28613a1e1	2	t
65810910-f9de-4177-b2c2-d2f794901723	db1e2f75-d2d4-4a3c-b6de-90f28613a1e1	3	t
d11f8f8d-71b9-45cc-b727-d3e03666a099	db1e2f75-d2d4-4a3c-b6de-90f28613a1e1	4	t
5aef93d2-6521-4007-a4df-ded7625116f9	db1e2f75-d2d4-4a3c-b6de-90f28613a1e1	5	t
0f977a76-550d-4403-a43d-ba5bbe78a3da	db1e2f75-d2d4-4a3c-b6de-90f28613a1e1	6	t
f944933b-c063-442f-b8e8-a32efc4e5044	db1e2f75-d2d4-4a3c-b6de-90f28613a1e1	7	t
4a3a62b3-617b-412d-8f31-7f3ccd22bdee	db1e2f75-d2d4-4a3c-b6de-90f28613a1e1	8	t
706140de-35f8-412d-9bcd-8a759d434e34	db1e2f75-d2d4-4a3c-b6de-90f28613a1e1	9	t
4b19cf60-4de1-4815-9064-823505c16f8a	db1e2f75-d2d4-4a3c-b6de-90f28613a1e1	10	t
\.


--
-- Data for Name: locker_shipment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.locker_shipment (id, order_id, locker_box_id, mode, status, pickup_code, placed_at, created_at) FROM stdin;
\.


--
-- Data for Name: order; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public."order" (id, reader_id, status, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: order_item; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.order_item (id, order_id, book_item_id, due_date, returned_at, created_at) FROM stdin;
\.


--
-- Data for Name: spatial_ref_sys; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.spatial_ref_sys (srid, auth_name, auth_srid, srtext, proj4text) FROM stdin;
\.


--
-- Data for Name: user; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public."user" (id, email, password, role, first_name, last_name, created_at) FROM stdin;
0f5e2ecc-3bad-4371-9129-083f831e15c0	anna.kowalska@example.com	$argon2id$v=19$m=65536,t=3,p=4$dCkKV5QWSa+dN+LVVnNdbw$WQJSFycoS3/x805ejrMHD6r3uA6pTIxBIJlCNHqDFUI	reader	Anna	Kowalska	2025-11-12 14:38:03.386594+00
7d4c0c01-28a5-4603-be6e-672834882dcd	piotr.nowak@example.com	$argon2id$v=19$m=65536,t=3,p=4$lBeG0GaybtNVUhAZCoeV4A$l4bRbmpUSos0l73ftR4dDuUkIOzlukJ6Qtl2FLd9D6U	reader	Piotr	Nowak	2025-11-12 14:38:03.386594+00
75afee38-d311-4c20-a4b9-f2872c844381	katarzyna.wisniewska@example.com	$argon2id$v=19$m=65536,t=3,p=4$lSdW3pR0lL7zdcbcPWnpOA$LKpshmIHlUCGcKCcXDeX0xKpFhB72ZiTZOZv+5yfw0w	librarian	Katarzyna	Wiśniewska	2025-11-12 14:38:03.386594+00
d9b66f3f-f1d9-434e-8671-385e2fb52867	tomasz.lewandowski@example.com	$argon2id$v=19$m=65536,t=3,p=4$33kBh3/C4A4R3auNJG+fHQ$KKnxo8cvQmrBBHCrS0Z4bPXdWI9Ynifi0pYOxsgOjL4	librarian	Tomasz	Lewandowski	2025-11-12 14:38:03.386594+00
02d3b9dd-2abd-448c-a40c-f991a28c9378	adam.zielinski@example.com	$argon2id$v=19$m=65536,t=3,p=4$oGHk1o8aIcfVzMfDRQ8nVg$3XMvTexu666rm1frgN5beihfjaD3bIimz4ewk3XP/B0	courier	Adam	Zieliński	2025-11-12 14:38:03.386594+00
d43b760d-829f-49af-9ba0-f17c79919ac3	magda.wrobel@example.com	$argon2id$v=19$m=65536,t=3,p=4$SHsnWC8yr3+d7KTSKzza0w$/7BxsXWcABOcTMUaFavxzx5y0PW/NwbHtmZx8q8DbX0	courier	Magdalena	Wróbel	2025-11-12 14:38:03.386594+00
\.


--
-- Data for Name: geocode_settings; Type: TABLE DATA; Schema: tiger; Owner: -
--

COPY tiger.geocode_settings (name, setting, unit, category, short_desc) FROM stdin;
\.


--
-- Data for Name: pagc_gaz; Type: TABLE DATA; Schema: tiger; Owner: -
--

COPY tiger.pagc_gaz (id, seq, word, stdword, token, is_custom) FROM stdin;
\.


--
-- Data for Name: pagc_lex; Type: TABLE DATA; Schema: tiger; Owner: -
--

COPY tiger.pagc_lex (id, seq, word, stdword, token, is_custom) FROM stdin;
\.


--
-- Data for Name: pagc_rules; Type: TABLE DATA; Schema: tiger; Owner: -
--

COPY tiger.pagc_rules (id, rule, is_custom) FROM stdin;
\.


--
-- Data for Name: topology; Type: TABLE DATA; Schema: topology; Owner: -
--

COPY topology.topology (id, name, srid, "precision", hasz) FROM stdin;
\.


--
-- Data for Name: layer; Type: TABLE DATA; Schema: topology; Owner: -
--

COPY topology.layer (topology_id, layer_id, schema_name, table_name, feature_column, feature_type, level, child_id) FROM stdin;
\.


--
-- Name: topology_id_seq; Type: SEQUENCE SET; Schema: topology; Owner: -
--

SELECT pg_catalog.setval('topology.topology_id_seq', 1, false);


--
-- Name: book_item book_item_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.book_item
    ADD CONSTRAINT book_item_pkey PRIMARY KEY (id);


--
-- Name: book book_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.book
    ADD CONSTRAINT book_pkey PRIMARY KEY (isbn);


--
-- Name: cart_item cart_item_cart_id_isbn_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cart_item
    ADD CONSTRAINT cart_item_cart_id_isbn_key UNIQUE (cart_id, isbn);


--
-- Name: cart_item cart_item_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cart_item
    ADD CONSTRAINT cart_item_pkey PRIMARY KEY (id);


--
-- Name: cart cart_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cart
    ADD CONSTRAINT cart_pkey PRIMARY KEY (id);


--
-- Name: locker_box locker_box_locker_id_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locker_box
    ADD CONSTRAINT locker_box_locker_id_number_key UNIQUE (locker_id, number);


--
-- Name: locker_box locker_box_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locker_box
    ADD CONSTRAINT locker_box_pkey PRIMARY KEY (id);


--
-- Name: locker locker_locker_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locker
    ADD CONSTRAINT locker_locker_code_key UNIQUE (locker_code);


--
-- Name: locker locker_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locker
    ADD CONSTRAINT locker_pkey PRIMARY KEY (id);


--
-- Name: locker_shipment locker_shipment_pickup_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locker_shipment
    ADD CONSTRAINT locker_shipment_pickup_code_key UNIQUE (pickup_code);


--
-- Name: locker_shipment locker_shipment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locker_shipment
    ADD CONSTRAINT locker_shipment_pkey PRIMARY KEY (id);


--
-- Name: order_item order_item_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_item
    ADD CONSTRAINT order_item_pkey PRIMARY KEY (id);


--
-- Name: order order_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."order"
    ADD CONSTRAINT order_pkey PRIMARY KEY (id);


--
-- Name: order_item uq_book_item_once; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_item
    ADD CONSTRAINT uq_book_item_once UNIQUE (book_item_id);


--
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: idx_book_authors; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_book_authors ON public.book USING gin (to_tsvector('simple'::regconfig, authors));


--
-- Name: idx_book_item_availability; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_book_item_availability ON public.book_item USING btree (is_available);


--
-- Name: idx_book_item_isbn; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_book_item_isbn ON public.book_item USING btree (isbn);


--
-- Name: idx_book_item_location; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_book_item_location ON public.book_item USING btree (current_location);


--
-- Name: idx_book_title; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_book_title ON public.book USING gin (to_tsvector('simple'::regconfig, title));


--
-- Name: idx_cart_item_cart_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cart_item_cart_id ON public.cart_item USING btree (cart_id);


--
-- Name: idx_cart_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cart_user_id ON public.cart USING btree (user_id);


--
-- Name: idx_locker_box_available; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_locker_box_available ON public.locker_box USING btree (is_available);


--
-- Name: idx_locker_city; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_locker_city ON public.locker USING btree (city);


--
-- Name: idx_locker_location; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_locker_location ON public.locker USING gist (location);


--
-- Name: idx_order_item_book_item; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_order_item_book_item ON public.order_item USING btree (book_item_id);


--
-- Name: idx_order_item_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_order_item_order ON public.order_item USING btree (order_id);


--
-- Name: idx_order_reader; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_order_reader ON public."order" USING btree (reader_id);


--
-- Name: idx_order_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_order_status ON public."order" USING btree (status);


--
-- Name: idx_shipment_mode; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_shipment_mode ON public.locker_shipment USING btree (mode);


--
-- Name: idx_shipment_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_shipment_order ON public.locker_shipment USING btree (order_id);


--
-- Name: idx_shipment_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_shipment_status ON public.locker_shipment USING btree (status);


--
-- Name: idx_user_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_role ON public."user" USING btree (role);


--
-- Name: uq_user_email_lower; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_user_email_lower ON public."user" USING btree (lower(email));


--
-- Name: cart trg_cart_updated; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_cart_updated BEFORE UPDATE ON public.cart FOR EACH ROW EXECUTE FUNCTION public.update_cart_timestamp();


--
-- Name: locker_shipment trg_locker_shipment_pickup_code; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_locker_shipment_pickup_code BEFORE INSERT ON public.locker_shipment FOR EACH ROW EXECUTE FUNCTION public.generate_pickup_code();


--
-- Name: order_item trg_order_item_sync; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_order_item_sync AFTER INSERT OR DELETE OR UPDATE ON public.order_item FOR EACH ROW EXECUTE FUNCTION public.sync_book_item_availability();


--
-- Name: order trg_order_updated; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_order_updated BEFORE UPDATE ON public."order" FOR EACH ROW EXECUTE FUNCTION public.update_order_timestamp();


--
-- Name: user trg_user_lower_email; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_lower_email BEFORE INSERT OR UPDATE ON public."user" FOR EACH ROW EXECUTE FUNCTION public.enforce_lowercase_email();


--
-- Name: book_item book_item_isbn_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.book_item
    ADD CONSTRAINT book_item_isbn_fkey FOREIGN KEY (isbn) REFERENCES public.book(isbn) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: cart_item cart_item_cart_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cart_item
    ADD CONSTRAINT cart_item_cart_id_fkey FOREIGN KEY (cart_id) REFERENCES public.cart(id) ON DELETE CASCADE;


--
-- Name: cart_item cart_item_isbn_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cart_item
    ADD CONSTRAINT cart_item_isbn_fkey FOREIGN KEY (isbn) REFERENCES public.book(isbn);


--
-- Name: cart cart_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cart
    ADD CONSTRAINT cart_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: locker_box locker_box_locker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locker_box
    ADD CONSTRAINT locker_box_locker_id_fkey FOREIGN KEY (locker_id) REFERENCES public.locker(id) ON DELETE CASCADE;


--
-- Name: locker_shipment locker_shipment_locker_box_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locker_shipment
    ADD CONSTRAINT locker_shipment_locker_box_id_fkey FOREIGN KEY (locker_box_id) REFERENCES public.locker_box(id);


--
-- Name: locker_shipment locker_shipment_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locker_shipment
    ADD CONSTRAINT locker_shipment_order_id_fkey FOREIGN KEY (order_id) REFERENCES public."order"(id) ON DELETE CASCADE;


--
-- Name: order_item order_item_book_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_item
    ADD CONSTRAINT order_item_book_item_id_fkey FOREIGN KEY (book_item_id) REFERENCES public.book_item(id);


--
-- Name: order_item order_item_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_item
    ADD CONSTRAINT order_item_order_id_fkey FOREIGN KEY (order_id) REFERENCES public."order"(id) ON DELETE CASCADE;


--
-- Name: order order_reader_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."order"
    ADD CONSTRAINT order_reader_id_fkey FOREIGN KEY (reader_id) REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

