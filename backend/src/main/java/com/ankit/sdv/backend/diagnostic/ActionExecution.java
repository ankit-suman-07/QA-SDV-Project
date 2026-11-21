package com.ankit.sdv.backend.diagnostic;

import java.util.Optional;

/** Selected-target executor boundary. A dispatch acknowledgement has no lifecycle evidence. */
interface ActionExecution {
    void dispatch(V2Action.Request request);
    Optional<V2Action.Result> result(V2Action.Request request);
}
