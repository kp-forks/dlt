import inspect
from types import ModuleType
from makefun import wraps
from typing import Any, Callable, Dict, Iterator, List, NamedTuple, Optional, Sequence, Tuple, Type, Union, overload

from dlt.common.configuration import with_config, get_fun_spec
from dlt.common.configuration.specs import BaseConfiguration
from dlt.common.exceptions import ArgumentsOverloadException
from dlt.common.schema.schema import Schema
from dlt.common.schema.typing import TTableSchemaColumns, TWriteDisposition
from dlt.common.source import TTableHintTemplate, TFunHintTemplate
from dlt.common.typing import AnyFun, TFun, ParamSpec
from dlt.common.utils import is_inner_function
from dlt.extract.sources import DltResource, DltSource


class SourceInfo(NamedTuple):
    SPEC: Type[BaseConfiguration]
    f: AnyFun
    module: ModuleType


_SOURCES: Dict[str, SourceInfo] = {}

TSourceFunParams = ParamSpec("TSourceFunParams")
TResourceFunParams = ParamSpec("TResourceFunParams")


@overload
def source(func: Callable[TSourceFunParams, Any], /, name: str = None, schema: Schema = None, spec: Type[BaseConfiguration] = None) -> Callable[TSourceFunParams, DltSource]:
    ...

@overload
def source(func: None = ..., /, name: str = None, schema: Schema = None, spec: Type[BaseConfiguration] = None) -> Callable[[Callable[TSourceFunParams, Any]], Callable[TSourceFunParams, DltSource]]:
    ...

def source(func: Optional[AnyFun] = None, /, name: str = None, schema: Schema = None, spec: Type[BaseConfiguration] = None) -> Any:

    if name and schema:
        raise ArgumentsOverloadException("Source name cannot be set if schema is present")

    def decorator(f: Callable[TSourceFunParams, Any]) -> Callable[TSourceFunParams, DltSource]:
        nonlocal schema, name

        # extract name
        if schema:
            name = schema.name
        else:
            name = name or f.__name__
            # create or load default schema
            # TODO: we need a convention to load ie. load the schema from file with name_schema.yaml
            schema = Schema(name)

        # wrap source extraction function in configuration with namespace
        conf_f = with_config(f, spec=spec, namespaces=("source", name))

        @wraps(conf_f, func_name=name)
        def _wrap(*args: Any, **kwargs: Any) -> DltSource:
            rv = conf_f(*args, **kwargs)
            # if generator, consume it immediately
            if inspect.isgenerator(rv):
                rv = list(rv)

            def check_rv_type(rv: Any) -> None:
                pass

            # check if return type is list or tuple
            if isinstance(rv, (list, tuple)):
                # check all returned elements
                for v in rv:
                    check_rv_type(v)
            else:
                check_rv_type(rv)

            # convert to source
            return DltSource.from_data(schema, rv)

        # get spec for wrapped function
        SPEC = get_fun_spec(conf_f)
        # store the source information
        _SOURCES[_wrap.__qualname__] = SourceInfo(SPEC, _wrap, inspect.getmodule(f))

        # the typing is right, but makefun.wraps does not preserve signatures
        return _wrap  # type: ignore

    if func is None:
        # we're called with parens.
        return decorator

    if not callable(func):
        raise ValueError("First parameter to the source must be callable ie. by using it as function decorator")

    # we're called as @source without parens.
    return decorator(func)


# @source
# def reveal_1() -> None:
#     pass

# @source(name="revel")
# def reveal_2() -> None:
#     pass


# def revel_3(v) -> int:
#     pass


# reveal_type(reveal_1)
# reveal_type(reveal_1())

# reveal_type(reveal_2)
# reveal_type(reveal_2())

# reveal_type(source(revel_3))
# reveal_type(source(revel_3)("s"))

@overload
def resource(
    data: Callable[TResourceFunParams, Any],
    /,
    name: str = None,
    table_name_fun: TFunHintTemplate[str] = None,
    write_disposition: TTableHintTemplate[TWriteDisposition] = None,
    columns: TTableHintTemplate[TTableSchemaColumns] = None,
    selected: bool = True,
    depends_on: DltResource = None,
    spec: Type[BaseConfiguration] = None
) -> Callable[TResourceFunParams, DltResource]:
    ...

@overload
def resource(
    data: None = ...,
    /,
    name: str = None,
    table_name_fun: TFunHintTemplate[str] = None,
    write_disposition: TTableHintTemplate[TWriteDisposition] = None,
    columns: TTableHintTemplate[TTableSchemaColumns] = None,
    selected: bool = True,
    depends_on: DltResource = None,
    spec: Type[BaseConfiguration] = None
) -> Callable[[Callable[TResourceFunParams, Any]], Callable[TResourceFunParams, DltResource]]:
    ...


# @overload
# def resource(
#     data: Union[DltSource, DltResource, Sequence[DltSource], Sequence[DltResource]],
#     /
# ) -> DltResource:
#     ...


@overload
def resource(
    data: Union[List[Any], Tuple[Any], Iterator[Any]],
    /,
    name: str = None,
    table_name_fun: TFunHintTemplate[str] = None,
    write_disposition: TTableHintTemplate[TWriteDisposition] = None,
    columns: TTableHintTemplate[TTableSchemaColumns] = None,
    selected: bool = True,
    depends_on: DltResource = None,
    spec: Type[BaseConfiguration] = None
) -> DltResource:
    ...


def resource(
    data: Optional[Any] = None,
    /,
    name: str = None,
    table_name_fun: TFunHintTemplate[str] = None,
    write_disposition: TTableHintTemplate[TWriteDisposition] = None,
    columns: TTableHintTemplate[TTableSchemaColumns] = None,
    selected: bool = True,
    depends_on: DltResource = None,
    spec: Type[BaseConfiguration] = None
) -> Any:

    def make_resource(_name: str, _data: Any) -> DltResource:
        table_template = DltResource.new_table_template(table_name_fun or _name, write_disposition=write_disposition, columns=columns)
        return DltResource.from_data(_data, _name, table_template, selected, depends_on)


    def decorator(f: Callable[TResourceFunParams, Any]) -> Callable[TResourceFunParams, DltResource]:
        resource_name = name or f.__name__

        # if f is not a generator (does not yield) raise Exception
        if not inspect.isgeneratorfunction(inspect.unwrap(f)):
            raise ResourceFunNotGenerator()

        # do not inject config values for inner functions, we assume that they are part of the source
        SPEC: Type[BaseConfiguration] = None
        if is_inner_function(f):
            conf_f = f
        else:
            print("USE SPEC -> GLOBAL")
            # wrap source extraction function in configuration with namespace
            conf_f = with_config(f, spec=spec, namespaces=("resource", resource_name))
            # get spec for wrapped function
            SPEC = get_fun_spec(conf_f)

        @wraps(conf_f, func_name=resource_name)
        def _wrap(*args: Any, **kwargs: Any) -> DltResource:
            return make_resource(resource_name, f(*args, **kwargs))

        # store the standalone resource information
        if SPEC:
            _SOURCES[_wrap.__qualname__] = SourceInfo(SPEC, _wrap, inspect.getmodule(f))

        # the typing is right, but makefun.wraps does not preserve signatures
        return _wrap  # type: ignore


    # if data is callable or none use decorator
    if data is None:
        # we're called with parens.
        return decorator

    if callable(data):
        return decorator(data)
    else:
        return make_resource(name, data)


def _get_source_for_inner_function(f: AnyFun) -> Optional[SourceInfo]:
    # find source function
    parts = f.__qualname__.split(".")
    parent_fun = ".".join(parts[:-2])
    return _SOURCES.get(parent_fun)


# @resource
# def reveal_1() -> None:
#     pass

# @resource(name="revel")
# def reveal_2() -> None:
#     pass


# def revel_3(v) -> int:
#     pass


# reveal_type(reveal_1)
# reveal_type(reveal_1())

# reveal_type(reveal_2)
# reveal_type(reveal_2())

# reveal_type(resource(revel_3))
# reveal_type(resource(revel_3)("s"))


# reveal_type(resource([], name="aaaa"))
# reveal_type(resource("aaaaa", name="aaaa"))